package bus

import (
	"context"
	"encoding/json/jsontext"
	"encoding/json/v2"
	"strings"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"github.com/tbhb/agent-orchestration-poc/internal/core/relay"
)

func relayCall(t *testing.T, client testClient, group, agent, operation string, request relayRequest) relayResponse {
	t.Helper()
	request.ID = "request"
	reply := "grp." + group + ".relay.reply." + agent + ".request"
	sub := subscribeReply(t, client.conn, reply)
	defer func() { _ = sub.Unsubscribe() }()
	data, err := json.Marshal(request)
	if err != nil {
		t.Fatal(err)
	}
	if err := client.conn.Publish("grp."+group+".relay.req."+operation+"."+agent, data); err != nil {
		t.Fatal(err)
	}
	message, err := sub.NextMsg(8 * time.Second)
	if err != nil {
		t.Fatal(err)
	}
	var response relayResponse
	if err := json.Unmarshal(message.Data, &response); err != nil {
		t.Fatal(err)
	}
	return response
}

func TestRelayFlow(t *testing.T) {
	broker := testBus(t)
	alice := connectTest(t, broker, "build", "alice")
	bob := connectTest(t, broker, "build", "bob")
	message := relayRequest{Destination: "dm", To: "bob", Envelope: jsontext.Value(`{"body":"hello"}`), MessageID: "same"}
	stored, other := checkRelaySend(t, alice, bob, message)
	checkRelayDelivery(t, alice, bob, stored, other)
	checkRelayReads(t, broker, alice)
	checkRelayFailures(t, broker, alice, message)
}

func checkRelaySend(t *testing.T, alice, bob testClient, message relayRequest) (relayResponse, relayResponse) {
	t.Helper()
	stored := relayCall(t, alice, "build", "alice", "send", message)
	if stored.Result != "stored" || stored.Sequence == 0 {
		t.Fatalf("stored: %+v", stored)
	}
	duplicate := relayCall(t, alice, "build", "alice", "send", message)
	if duplicate.Result != "duplicate" || duplicate.Sequence != stored.Sequence {
		t.Fatalf("duplicate: %+v", duplicate)
	}
	other := relayCall(t, bob, "build", "bob", "send", relayRequest{Destination: "all", Envelope: jsontext.Value(`{"body":"other"}`), MessageID: "same"})
	if other.Result != "stored" || other.Sequence == stored.Sequence {
		t.Fatalf("cross-agent duplicate id: %+v", other)
	}
	rejected := relayCall(t, alice, "build", "alice", "send", relayRequest{Destination: "dm", To: "bad.name", Envelope: message.Envelope})
	if rejected.Result != "rejected" {
		t.Fatalf("rejected: %+v", rejected)
	}
	t.Logf("stored sequence=%d, duplicate sequence=%d, cross-agent stored sequence=%d", stored.Sequence, duplicate.Sequence, other.Sequence)
	return stored, other
}

func checkRelayDelivery(t *testing.T, alice, bob testClient, stored, other relayResponse) {
	t.Helper()
	delivered := relayCall(t, bob, "build", "bob", "receive", relayRequest{TimeoutMS: 500})
	if delivered.Result != "delivered" || delivered.Sequence != stored.Sequence || delivered.Subject != "grp.build.msg.dm.bob.alice" || delivered.Token == "" || strings.Contains(delivered.Token, "$JS.ACK") {
		t.Fatalf("delivered: %+v", delivered)
	}
	if result := relayCall(t, alice, "build", "alice", "ack", relayRequest{Token: delivered.Token}); result.Result != "unknown-token" {
		t.Fatalf("foreign ack: %+v", result)
	}
	if result := relayCall(t, bob, "build", "bob", "ack", relayRequest{Token: "not-a-token"}); result.Result != "unknown-token" {
		t.Fatalf("unknown ack: %+v", result)
	}
	if result := relayCall(t, bob, "build", "bob", "ack", relayRequest{Token: delivered.Token}); result.Result != "acked" {
		t.Fatalf("ack: %+v", result)
	}
	if result := relayCall(t, bob, "build", "bob", "ack", relayRequest{Token: delivered.Token}); result.Result != "unknown-token" {
		t.Fatalf("duplicate ack: %+v", result)
	}
	if result := relayCall(t, bob, "build", "bob", "receive", relayRequest{TimeoutMS: 100}); result.Result != "delivered" || result.Sequence != other.Sequence {
		t.Fatalf("next message: %+v", result)
	}
	t.Log("fetch=delivered, foreign token=unknown-token, ack=acked, duplicate token=unknown-token")
}

func checkRelayReads(t *testing.T, broker *Bus, alice testClient) {
	t.Helper()
	for _, operation := range []string{"status", "roster"} {
		if result := relayCall(t, alice, "build", "alice", operation, relayRequest{Key: "alice"}); result.Result != "not-provisioned" {
			t.Fatalf("%s missing bucket: %+v", operation, result)
		}
	}
	operator := connectTest(t, broker, "build", "operator")
	js, err := jetstream.New(operator.conn)
	if err != nil {
		t.Fatal(err)
	}
	for _, operation := range []string{"status", "roster"} {
		bucket, err := js.CreateKeyValue(t.Context(), jetstream.KeyValueConfig{Bucket: operation})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := bucket.Put(t.Context(), "alice", []byte(`{"state":"ready"}`)); err != nil {
			t.Fatal(err)
		}
		if result := relayCall(t, alice, "build", "alice", operation, relayRequest{Key: "alice"}); result.Result != "found" || string(result.Value) != `{"state":"ready"}` {
			t.Fatalf("%s found: %+v", operation, result)
		}
		if result := relayCall(t, alice, "build", "alice", operation, relayRequest{Key: "missing"}); result.Result != "not-found" {
			t.Fatalf("%s absent key: %+v", operation, result)
		}
	}
	t.Log("status and roster: absent bucket=not-provisioned, populated key=found, absent key=not-found")
}

func checkRelayFailures(t *testing.T, broker *Bus, alice testClient, message relayRequest) {
	t.Helper()
	operator := connectTest(t, broker, "build", "operator")
	js, err := jetstream.New(operator.conn)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	unknown := broker.relays[0].send(ctx, relay.Request{Group: "build", Agent: "alice"}, message)
	if unknown.Result != "unknown" {
		t.Fatalf("timed out send claimed success: %+v", unknown)
	}
	if err := js.DeleteStream(t.Context(), "GROUP_BUILD"); err != nil {
		t.Fatal(err)
	}
	if result := relayCall(t, alice, "build", "alice", "send", message); result.Result != "unknown" {
		t.Fatalf("broker rejection claimed success: %+v", result)
	}
	t.Log("invalid destination=rejected, canceled publish=unknown, absent stream=unknown")
}

func TestRelayAttackMatrix(t *testing.T) {
	broker := testBus(t)
	alice := connectTest(t, broker, "build", "alice")
	bob := connectTest(t, broker, "build", "bob")
	operator := connectTest(t, broker, "build", "operator")
	js, stream := openTestStream(t, broker)
	if _, err := js.Publish(t.Context(), "grp.build.msg.dm.bob.alice", []byte(`{"body":"private"}`)); err != nil {
		t.Fatal(err)
	}
	consumer, err := stream.Consumer(t.Context(), "bob")
	if err != nil {
		t.Fatal(err)
	}
	before, err := consumer.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	checkRelayForeignGrants(t, alice)
	for _, reply := range []string{"grp.build.msg.all.bob", "grp.build.relay.req.send.bob", "grp.build.relay.reply.bob.request", "_INBOX.bob.attack"} {
		for _, operation := range []string{"send", "receive", "ack", "status", "roster"} {
			attackRelayReply(t, alice, operator, reply, operation)
		}
	}
	after, err := consumer.Info(t.Context())
	if err != nil || after.Delivered != before.Delivered || after.AckFloor != before.AckFloor {
		t.Fatalf("victim consumer changed after forged receive: before=%+v after=%+v error=%v", before.Delivered, after.Delivered, err)
	}
	delivered := relayCall(t, bob, "build", "bob", "receive", relayRequest{TimeoutMS: 100})
	if delivered.Result != "delivered" || delivered.Subject != "grp.build.msg.dm.bob.alice" {
		t.Fatalf("victim private message unavailable: %+v", delivered)
	}
	if result := relayCall(t, bob, "build", "bob", "ack", relayRequest{Token: delivered.Token}); result.Result != "acked" {
		t.Fatalf("victim ack: %+v", result)
	}
	t.Log("foreign subjects denied, forged payload identity ignored, malicious reply had no victim delivery or consumer progress")
}

func checkRelayForeignGrants(t *testing.T, alice testClient) {
	t.Helper()
	for _, subject := range []string{
		"grp.build.relay.req.send.bob", "grp.other.relay.req.send.alice",
		"grp.build.relay.reply.bob.request", "grp.build.msg.all.alice",
	} {
		expectPublishDenied(t, alice, subject)
	}
	for _, subject := range []string{"grp.build.relay.reply.bob.>", "grp.build.msg.dm.bob.*"} {
		expectSubscribeDenied(t, alice, subject)
	}
}

func attackRelayReply(t *testing.T, alice, operator testClient, target, operation string) {
	t.Helper()
	observer := subscribeReply(t, operator.conn, target)
	defer func() { _ = observer.Unsubscribe() }()
	legitimate := subscribeReply(t, alice.conn, "grp.build.relay.reply.alice.attack")
	defer func() { _ = legitimate.Unsubscribe() }()
	data := []byte(`{"id":"attack","destination":"dm","to":"alice","envelope":{"body":"safe"},"token":"forged","key":"alice","timeout_ms":50,"agent":"bob","consumer":"bob"}`)
	if err := alice.conn.PublishRequest("grp.build.relay.req."+operation+".alice", target, data); err != nil {
		t.Fatal(err)
	}
	if _, err := legitimate.NextMsg(2 * time.Second); err != nil {
		t.Fatalf("%s to %s lost legitimate response: %v", operation, target, err)
	}
	if msg, err := observer.NextMsg(50 * time.Millisecond); err != nats.ErrTimeout {
		t.Fatalf("%s published to victim target %s: %v, %v", operation, target, msg, err)
	}
}

func TestRelayOutOfOrderDelivery(t *testing.T) {
	broker := testBus(t)
	alice := connectTest(t, broker, "build", "alice")
	_, stream := openTestStream(t, broker)
	info, err := stream.Consumer(t.Context(), "alice")
	if err != nil {
		t.Fatal(err)
	}
	config, err := info.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	config.Config.AckWait = 20 * time.Millisecond
	consumer, err := stream.CreateOrUpdateConsumer(t.Context(), config.Config)
	if err != nil {
		t.Fatal(err)
	}
	stored := relayCall(t, alice, "build", "alice", "send", relayRequest{Destination: "all", Envelope: jsontext.Value(`{"body":"ordering"}`)})
	if stored.Result != "stored" {
		t.Fatal(stored)
	}
	fetch := func() jetstream.Msg {
		t.Helper()
		batch, err := consumer.Fetch(1, jetstream.FetchMaxWait(time.Second))
		if err != nil {
			t.Fatal(err)
		}
		message := <-batch.Messages()
		if message == nil {
			t.Fatalf("fetch: %v", batch.Error())
		}
		return message
	}
	first := fetch()
	time.Sleep(40 * time.Millisecond)
	second := fetch()
	firstMeta, firstErr := first.Metadata()
	secondMeta, secondErr := second.Metadata()
	if firstErr != nil || secondErr != nil || firstMeta.Sequence.Consumer >= secondMeta.Sequence.Consumer || firstMeta.Sequence.Stream != secondMeta.Sequence.Stream {
		t.Fatalf("expected two generations: first=%+v second=%+v errors=%v,%v", firstMeta, secondMeta, firstErr, secondErr)
	}
	newer := broker.relays[0].hold(relay.Request{Group: "build", Agent: "alice"}, "GROUP_BUILD", second)
	stale := broker.relays[0].hold(relay.Request{Group: "build", Agent: "alice"}, "GROUP_BUILD", first)
	if stale.Result == "delivered" {
		t.Fatalf("stale generation replaced newer: %+v", stale)
	}
	if newer.Result != "delivered" {
		t.Fatalf("newer generation: %+v", newer)
	}
	if result := relayCall(t, alice, "build", "alice", "ack", relayRequest{Token: newer.Token}); result.Result != "acked" {
		t.Fatalf("newer token invalidated: %+v", result)
	}
}

func TestRelayRestartToken(t *testing.T) {
	state := t.TempDir()
	first := startSingleAgentBus(t, state)
	alice := connectTest(t, first, "build", "alice")
	result := relayCall(t, alice, "build", "alice", "send", relayRequest{Destination: "all", Envelope: jsontext.Value(`{"body":"restart"}`)})
	if result.Result != "stored" {
		t.Fatal(result)
	}
	old := relayCall(t, alice, "build", "alice", "receive", relayRequest{TimeoutMS: 100})
	if old.Result != "delivered" {
		t.Fatal(old)
	}
	alice.conn.Close()
	first.Close()
	second := startSingleAgentBus(t, state)
	t.Cleanup(second.Close)
	alice = connectTest(t, second, "build", "alice")
	if response := relayCall(t, alice, "build", "alice", "ack", relayRequest{Token: old.Token}); response.Result != "unknown-token" {
		t.Fatalf("old token: %+v", response)
	}
	// The durable's default AckWait is 30 seconds. Its redelivery must carry a new token.
	time.Sleep(31 * time.Second)
	fresh := relayCall(t, alice, "build", "alice", "receive", relayRequest{TimeoutMS: 1000})
	if fresh.Result != "delivered" || fresh.Token == old.Token || fresh.Sequence != old.Sequence {
		t.Fatalf("redelivery: %+v", fresh)
	}
	if response := relayCall(t, alice, "build", "alice", "ack", relayRequest{Token: fresh.Token}); response.Result != "acked" {
		t.Fatalf("redelivered ack: %+v", response)
	}
	t.Log("post-restart token=unknown-token, redelivery token=fresh, redelivery ack=acked")
}
