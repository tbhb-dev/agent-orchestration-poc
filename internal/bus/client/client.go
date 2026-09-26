// Package client performs agentctl broker effects using an agent credential file.
package client

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"github.com/tbhb/agent-orchestration-poc/internal/core/command"
	"github.com/tbhb/agent-orchestration-poc/internal/core/envelope"
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
	"github.com/tbhb/agent-orchestration-poc/internal/core/render"
	"github.com/tbhb/agent-orchestration-poc/internal/core/state"
)

var ErrTimeout = errors.New("no message before timeout")

// Client owns one broker connection.
type Client struct {
	conn *nats.Conn
	js   jetstream.JetStream
	errs chan error
}

// Connect authenticates with a file path and dials IPv4 loopback.
func Connect(value command.Value) (*Client, error) {
	option, err := nats.NkeyOptionFromSeed(value.CredsFile)
	if err != nil {
		return nil, fmt.Errorf("read credential file: %w", err)
	}
	url := "nats://127.0.0.1:" + strconv.Itoa(value.Port)
	errs := make(chan error, 8)
	conn, err := nats.Connect(url, option, nats.Timeout(3*time.Second), nats.ErrorHandler(func(_ *nats.Conn, _ *nats.Subscription, err error) {
		select {
		case errs <- err:
		default:
		}
	}))
	if err != nil {
		return nil, fmt.Errorf("connect to bus: %w", err)
	}
	js, err := jetstream.New(conn)
	if err != nil {
		conn.Close()
		return nil, err
	}
	return &Client{conn: conn, js: js, errs: errs}, nil
}

// Close releases the broker connection.
func (client *Client) Close() { client.conn.Close() }

// Run executes a validated command against the bus.
func (client *Client) Run(ctx context.Context, value command.Value) (render.Result, error) {
	result, err := client.run(ctx, value)
	if err != nil {
		select {
		case brokerError := <-client.errs:
			return render.Result{}, fmt.Errorf("bus: %w", brokerError)
		default:
		}
	}
	return result, err
}

func (client *Client) run(ctx context.Context, value command.Value) (render.Result, error) {
	switch value.Name {
	case "send":
		return client.send(ctx, value)
	case "receive":
		return client.receive(ctx, value)
	case "ack":
		return client.ack(value)
	case "join":
		return client.join(ctx, value)
	case "status":
		return client.status(ctx, value)
	case "roster":
		return client.roster(ctx, value)
	default:
		return render.Result{}, fmt.Errorf("unsupported command %s", value.Name)
	}
}

func (client *Client) send(ctx context.Context, value command.Value) (render.Result, error) {
	id := value.ID
	if id == "" {
		var err error
		id, err = randomID()
		if err != nil {
			return render.Result{}, err
		}
	}
	message := envelope.Message{Body: envelope.Body{Text: value.Text}, Headers: envelope.Headers{
		ID: id, CorrelationID: value.CorrelationID, ReplyToID: value.ReplyToID,
		Kind: command.Kind(value), Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
	}}
	if value.Wait > 0 {
		message.Headers.CorrelationID = id
	}
	return client.publishAndMaybeWait(ctx, value, message)
}

func randomID() (string, error) {
	var data [16]byte
	if _, err := rand.Read(data[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(data[:]), nil
}

func (client *Client) publishAndMaybeWait(ctx context.Context, value command.Value, message envelope.Message) (render.Result, error) {
	var subscription *nats.Subscription
	if value.Wait > 0 {
		filter, err := command.ReplyFilter(value)
		if err != nil {
			return render.Result{}, err
		}
		subscription, err = client.conn.SubscribeSync(filter)
		if err != nil {
			return render.Result{}, err
		}
		defer func() { _ = subscription.Unsubscribe() }()
		if err := client.conn.Flush(); err != nil {
			return render.Result{}, err
		}
	}
	subject, err := command.Subject(value)
	if err != nil {
		return render.Result{}, err
	}
	body, headers, err := envelope.Encode(message)
	if err != nil {
		return render.Result{}, err
	}
	msg := &nats.Msg{Subject: subject, Data: body, Header: nats.Header{}}
	for key, field := range headers {
		msg.Header.Set(key, field)
	}
	if _, err := client.js.PublishMsg(ctx, msg); err != nil {
		return render.Result{}, err
	}
	if subscription != nil {
		return waitForReply(subscription, value.Wait, message.Headers.ID)
	}
	return render.Result{OK: true, Command: "send", ID: message.Headers.ID, To: value.To}, nil
}

func waitForReply(subscription *nats.Subscription, wait time.Duration, correlationID string) (render.Result, error) {
	deadline := time.Now().Add(wait)
	for time.Until(deadline) > 0 {
		msg, err := subscription.NextMsg(time.Until(deadline))
		if errors.Is(err, nats.ErrTimeout) {
			return render.Result{}, ErrTimeout
		}
		if err != nil {
			return render.Result{}, err
		}
		reply, err := envelope.Decode(msg.Data, plainHeaders(msg.Header))
		if err != nil || !envelope.IsReplyTo(reply, correlationID) {
			continue
		}
		return render.Result{OK: true, Command: "send", ID: correlationID, Message: &reply}, nil
	}
	return render.Result{}, ErrTimeout
}

func plainHeaders(headers nats.Header) map[string]string {
	values := make(map[string]string, len(headers))
	for key := range headers {
		values[key] = headers.Get(key)
	}
	return values
}

func (client *Client) receive(ctx context.Context, value command.Value) (render.Result, error) {
	definition, err := layout.Stream(value.Group)
	if err != nil {
		return render.Result{}, err
	}
	consumer, err := layout.Consumer(value.Group, value.Agent)
	if err != nil {
		return render.Result{}, err
	}
	inbox, err := client.js.Consumer(ctx, definition.Name, consumer.Name)
	if err != nil {
		return render.Result{}, err
	}
	batch, err := inbox.Fetch(1, jetstream.FetchMaxWait(value.Timeout))
	if err != nil {
		return render.Result{}, err
	}
	msg, ok := <-batch.Messages()
	if !ok {
		if err := batch.Error(); err != nil {
			return render.Result{}, err
		}
		return render.Result{}, ErrTimeout
	}
	decoded, err := envelope.Decode(msg.Data(), plainHeaders(msg.Headers()))
	if err != nil {
		return render.Result{}, err
	}
	return render.Result{OK: true, Command: "receive", ID: msg.Reply(), From: command.Sender(msg.Subject()), Message: &decoded}, nil
}

func (client *Client) ack(value command.Value) (render.Result, error) {
	if !command.ValidAckSubject(value, value.ID) {
		return render.Result{}, errors.New("ack ID is not for this agent's consumer")
	}
	if err := client.conn.Publish(value.ID, []byte("+ACK")); err != nil {
		return render.Result{}, err
	}
	if err := client.conn.Flush(); err != nil {
		return render.Result{}, err
	}
	return render.Result{OK: true, Command: "ack", ID: value.ID}, nil
}

func (client *Client) bucket(ctx context.Context, name string) (jetstream.KeyValue, error) {
	bucket, err := client.js.KeyValue(ctx, name)
	if errors.Is(err, jetstream.ErrBucketNotFound) {
		return client.js.CreateKeyValue(ctx, jetstream.KeyValueConfig{Bucket: name})
	}
	return bucket, err
}

func (client *Client) join(ctx context.Context, value command.Value) (render.Result, error) {
	bucket, err := client.bucket(ctx, "roster")
	if err != nil {
		return render.Result{}, err
	}
	entry := state.Roster{Role: command.Role(value), JoinedAt: time.Now().UTC().Format(time.RFC3339Nano)}
	data, err := state.EncodeRoster(entry)
	if err != nil {
		return render.Result{}, err
	}
	if _, err := bucket.Create(ctx, value.Agent, data); err != nil && !errors.Is(err, jetstream.ErrKeyExists) {
		return render.Result{}, err
	}
	statusBucket, err := client.bucket(ctx, "status")
	if err != nil {
		return render.Result{}, err
	}
	idle, err := state.EncodeStatus(state.Status{State: "idle", UpdatedAt: time.Now().UTC().Format(time.RFC3339Nano)})
	if err != nil {
		return render.Result{}, err
	}
	if _, err := statusBucket.Create(ctx, value.Agent, idle); err != nil && !errors.Is(err, jetstream.ErrKeyExists) {
		return render.Result{}, err
	}
	result, err := client.roster(ctx, value)
	result.Command = "join"
	result.Role = command.Role(value)
	result.Instructions = command.JoinInstructions()
	return result, err
}

func (client *Client) status(ctx context.Context, value command.Value) (render.Result, error) {
	bucket, err := client.bucket(ctx, "status")
	if err != nil {
		return render.Result{}, err
	}
	if value.Set != "" {
		data, err := state.EncodeStatus(state.Status{State: value.Set, Detail: value.Detail, UpdatedAt: time.Now().UTC().Format(time.RFC3339Nano)})
		if err != nil {
			return render.Result{}, err
		}
		if _, err := bucket.Put(ctx, value.Agent, data); err != nil {
			return render.Result{}, err
		}
	}
	entry, err := bucket.Get(ctx, value.Agent)
	if err != nil {
		return render.Result{}, err
	}
	status, err := state.DecodeStatus(entry.Value())
	return render.Result{OK: err == nil, Command: "status", Status: status.State, Detail: status.Detail}, err
}

func (client *Client) roster(ctx context.Context, _ command.Value) (render.Result, error) {
	bucket, err := client.bucket(ctx, "roster")
	if err != nil {
		return render.Result{}, err
	}
	keys, err := bucket.Keys(ctx)
	if errors.Is(err, jetstream.ErrNoKeysFound) {
		return render.Result{OK: true, Command: "roster", Roster: map[string]state.Roster{}}, nil
	}
	if err != nil {
		return render.Result{}, err
	}
	entries := make(map[string]state.Roster, len(keys))
	for _, key := range keys {
		entry, err := bucket.Get(ctx, key)
		if err != nil {
			return render.Result{}, err
		}
		entries[key], err = state.DecodeRoster(entry.Value())
		if err != nil {
			return render.Result{}, err
		}
	}
	return render.Result{OK: true, Command: "roster", Roster: entries}, nil
}
