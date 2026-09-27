package bus

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json/jsontext"
	"encoding/json/v2"
	"errors"
	"sync"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
	"github.com/tbhb/agent-orchestration-poc/internal/core/relay"
)

type relayRequest struct {
	ID          string         `json:"id"`
	Destination string         `json:"destination,omitempty"`
	To          string         `json:"to,omitempty"`
	Envelope    jsontext.Value `json:"envelope,omitempty"`
	MessageID   string         `json:"message_id,omitempty"`
	Token       string         `json:"token,omitempty"`
	Key         string         `json:"key,omitempty"`
	TimeoutMS   int            `json:"timeout_ms,omitempty"`
}

type relayResponse struct {
	Result   string         `json:"result"`
	Sequence uint64         `json:"sequence,omitempty"`
	Subject  string         `json:"subject,omitempty"`
	Envelope jsontext.Value `json:"envelope,omitempty"`
	Token    string         `json:"token,omitempty"`
	Value    []byte         `json:"value,omitempty"`
}

type heldDelivery struct {
	owner relay.Delivery
	msg   jetstream.Msg
}

type relayServer struct {
	group string
	conn  *nats.Conn
	js    jetstream.JetStream
	mu    sync.Mutex
	held  map[string]heldDelivery
}

func (b *Bus) startRelay(group, operatorPath string) (*relayServer, error) {
	option, err := nats.NkeyOptionFromSeed(operatorPath)
	if err != nil {
		return nil, err
	}
	conn, err := nats.Connect(b.URL(), option)
	if err != nil {
		return nil, err
	}
	js, err := jetstream.New(conn)
	if err != nil {
		conn.Close()
		return nil, err
	}
	service := &relayServer{group: group, conn: conn, js: js, held: make(map[string]heldDelivery)}
	_, err = conn.Subscribe("grp."+group+".relay.req.>", func(msg *nats.Msg) {
		go service.handle(msg)
	})
	if err == nil {
		err = conn.Flush()
	}
	if err != nil {
		conn.Close()
		return nil, err
	}
	return service, nil
}

func (s *relayServer) handle(msg *nats.Msg) {
	identity, err := relay.ParseRequest(s.group, msg.Subject)
	if err != nil || len(msg.Data) > 128*1024 {
		return
	}
	var request relayRequest
	if json.Unmarshal(msg.Data, &request) != nil {
		return
	}
	reply, err := relay.Reply(identity, request.ID)
	if err != nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
	defer cancel()
	result := s.dispatch(ctx, identity, request)
	data, err := json.Marshal(result)
	if err == nil {
		_ = s.conn.Publish(reply, data)
	}
}

func (s *relayServer) dispatch(ctx context.Context, identity relay.Request, request relayRequest) relayResponse {
	switch identity.Operation {
	case "send":
		return s.send(ctx, identity, request)
	case "receive":
		return s.receive(ctx, identity, request)
	case "ack":
		return s.ack(ctx, identity, request)
	case "status", "roster":
		return s.read(ctx, identity, request)
	}
	return relayResponse{Result: "rejected"}
}

func (s *relayServer) send(ctx context.Context, identity relay.Request, request relayRequest) relayResponse {
	subject, err := relay.SendSubject(identity, request.Destination, request.To)
	if err != nil || !relay.ValidEnvelope(request.Envelope) {
		return relayResponse{Result: "rejected"}
	}
	id, err := relay.MessageID(identity, subject, request.MessageID)
	if err != nil {
		return relayResponse{Result: "rejected"}
	}
	definition, err := layout.Stream(identity.Group)
	if err != nil {
		return relayResponse{Result: "rejected"}
	}
	options := []jetstream.PublishOpt{jetstream.WithExpectStream(definition.Name)}
	if id != "" {
		options = append(options, jetstream.WithMsgID(id))
	}
	ack, err := s.js.Publish(ctx, subject, request.Envelope, options...)
	confirmed := relay.PublishAck{}
	if err == nil && ack != nil {
		confirmed = relay.PublishAck{Received: true, Stream: ack.Stream, Sequence: ack.Sequence, Duplicate: ack.Duplicate}
	}
	result, sequence := relay.ClassifyPublish(definition.Name, confirmed)
	return relayResponse{Result: result, Sequence: sequence}
}

func (s *relayServer) receive(ctx context.Context, identity relay.Request, request relayRequest) relayResponse {
	waitMS, valid := relay.ReceiveWait(request.TimeoutMS)
	if !valid {
		return relayResponse{Result: "rejected"}
	}
	definition, err := layout.Stream(identity.Group)
	if err != nil {
		return relayResponse{Result: "rejected"}
	}
	stream, err := s.js.Stream(ctx, definition.Name)
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	consumer, err := stream.Consumer(ctx, identity.Agent)
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	batch, err := consumer.Fetch(1, jetstream.FetchMaxWait(time.Duration(waitMS)*time.Millisecond))
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	message := <-batch.Messages()
	if message == nil {
		if batch.Error() != nil && !errors.Is(batch.Error(), context.DeadlineExceeded) {
			return relayResponse{Result: "unknown"}
		}
		return relayResponse{Result: "empty"}
	}
	return s.hold(identity, definition.Name, message)
}

func (s *relayServer) hold(identity relay.Request, stream string, message jetstream.Msg) relayResponse {
	metadata, err := message.Metadata()
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	owner, valid := relay.DeliveryFromMetadata(identity, stream, metadata.Stream, metadata.Consumer, metadata.Sequence.Stream, metadata.Sequence.Consumer)
	if !valid {
		return relayResponse{Result: "unknown"}
	}
	token, err := randomToken()
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	s.mu.Lock()
	owners := make(map[string]relay.Delivery, len(s.held))
	for old, held := range s.held {
		owners[old] = held.owner
	}
	install, remove := relay.PlanInstall(owners, owner)
	if !install {
		s.mu.Unlock()
		return relayResponse{Result: "unknown"}
	}
	for _, old := range remove {
		delete(s.held, old)
	}
	s.held[token] = heldDelivery{owner: owner, msg: message}
	s.mu.Unlock()
	return relayResponse{Result: "delivered", Sequence: owner.Sequence, Subject: message.Subject(), Envelope: jsontext.Value(message.Data()), Token: token}
}

func (s *relayServer) ack(ctx context.Context, identity relay.Request, request relayRequest) relayResponse {
	s.mu.Lock()
	held, exists := s.held[request.Token]
	if !relay.CanConsume(held.owner, exists, identity) {
		s.mu.Unlock()
		return relayResponse{Result: "unknown-token"}
	}
	delete(s.held, request.Token)
	s.mu.Unlock()
	if err := held.msg.DoubleAck(ctx); err != nil {
		return relayResponse{Result: "unknown"}
	}
	return relayResponse{Result: "acked"}
}

func (s *relayServer) read(ctx context.Context, identity relay.Request, request relayRequest) relayResponse {
	if layout.ValidToken(request.Key) != nil {
		return relayResponse{Result: "rejected"}
	}
	bucket, err := s.js.KeyValue(ctx, identity.Operation)
	if errors.Is(err, jetstream.ErrBucketNotFound) {
		return relayResponse{Result: "not-provisioned"}
	}
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	entry, err := bucket.Get(ctx, request.Key)
	if errors.Is(err, jetstream.ErrKeyNotFound) {
		return relayResponse{Result: "not-found"}
	}
	if err != nil {
		return relayResponse{Result: "unknown"}
	}
	return relayResponse{Result: "found", Value: entry.Value()}
}

func randomToken() (string, error) {
	var bytes [24]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(bytes[:]), nil
}
