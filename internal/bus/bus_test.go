package bus

import (
	"os"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

type testClient struct {
	conn *nats.Conn
	errs <-chan error
}

func testBus(t *testing.T) *Bus {
	t.Helper()
	broker, err := Start(t.Context(), Config{StateDir: t.TempDir(), Port: -1, Groups: []Group{
		{Name: "build", Agents: []string{"alice", "bob"}},
		{Name: "other", Agents: []string{"alice"}},
	}})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(broker.Close)
	return broker
}

func connectTest(t *testing.T, broker *Bus, group, agent string) testClient {
	t.Helper()
	path, err := broker.CredentialPath(group, agent)
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("credential mode %o", info.Mode().Perm())
	}
	option, err := nats.NkeyOptionFromSeed(path)
	if err != nil {
		t.Fatal(err)
	}
	errs := make(chan error, 8)
	conn, err := nats.Connect(broker.URL(), option, nats.ErrorHandler(func(_ *nats.Conn, _ *nats.Subscription, err error) {
		errs <- err
	}))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(conn.Close)
	return testClient{conn, errs}
}

func expectPermissionError(t *testing.T, errs <-chan error) {
	t.Helper()
	select {
	case <-errs:
	case <-time.After(time.Second):
		t.Fatal("expected permission error")
	}
}

func TestPublishPermissions(t *testing.T) {
	broker := testBus(t)
	operator := connectTest(t, broker, "build", "operator")
	alice := connectTest(t, broker, "build", "alice")
	bob := connectTest(t, broker, "build", "bob")
	other := connectTest(t, broker, "other", "alice")
	allowed, err := operator.conn.SubscribeSync("grp.build.msg.all.alice")
	if err != nil {
		t.Fatal(err)
	}
	if err := operator.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	expectPublishDenied(t, alice, "grp.build.msg.all.alice")
	for _, tc := range []struct {
		name    string
		client  testClient
		subject string
	}{
		{"alice as bob", alice, "grp.build.msg.all.bob"},
		{"bob as alice", bob, "grp.build.msg.all.alice"},
		{"other account", other, "grp.build.msg.all.alice"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			expectPublishDenied(t, tc.client, tc.subject)
		})
	}
	if _, err := allowed.NextMsg(100 * time.Millisecond); err != nats.ErrTimeout {
		t.Fatalf("forbidden publication delivered: %v", err)
	}
}

func TestAgentCannotPublishJetStreamControlSubjects(t *testing.T) {
	broker := testBus(t)
	alice := connectTest(t, broker, "build", "alice")
	for _, subject := range []string{
		"$JS.API.INFO",
		"$JS.API.STREAM.INFO.GROUP_BUILD",
		"$JS.API.CONSUMER.INFO.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.alice",
		"$JS.API.DIRECT.GET.GROUP_BUILD.grp.build.msg.all.alice",
		"$JS.API.any.future.route",
		"$JS.ACK.GROUP_BUILD.alice.1.1.1.1.1",
		"$JS.ACK.any.future.route",
	} {
		t.Run(subject, func(t *testing.T) {
			expectPublishDenied(t, alice, subject)
		})
	}
}

func TestSubscribePermissions(t *testing.T) {
	broker := testBus(t)
	alice := connectTest(t, broker, "build", "alice")
	other := connectTest(t, broker, "other", "alice")
	for _, tc := range []struct {
		name    string
		client  testClient
		subject string
	}{
		{"other direct", alice, "grp.build.msg.dm.bob.*"},
		{"other group", other, "grp.build.msg.all.*"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			expectSubscribeDenied(t, tc.client, tc.subject)
		})
	}
}

func expectPublishDenied(t *testing.T, client testClient, subject string) {
	t.Helper()
	if err := client.conn.Publish(subject, []byte("forbidden")); err != nil {
		t.Fatal(err)
	}
	if err := client.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	expectPermissionError(t, client.errs)
}

func expectSubscribeDenied(t *testing.T, client testClient, subject string) {
	t.Helper()
	if _, err := client.conn.SubscribeSync(subject); err != nil {
		t.Fatal(err)
	}
	if err := client.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	expectPermissionError(t, client.errs)
}

func TestStreamProvisioning(t *testing.T) {
	broker := testBus(t)
	if !strings.HasPrefix(broker.URL(), "nats://127.0.0.1:") {
		t.Fatalf("listener %q", broker.URL())
	}
	js, stream := openTestStream(t, broker)
	info, err := stream.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	if info.Config.Storage != jetstream.FileStorage || info.Config.Retention != jetstream.LimitsPolicy || info.Config.NoAck || !reflect.DeepEqual(info.Config.Subjects, []string{"grp.build.msg.>", "grp.build.evt.>"}) {
		t.Fatalf("stream config %+v", info.Config)
	}
	consumer, err := stream.Consumer(t.Context(), "alice")
	if err != nil {
		t.Fatal(err)
	}
	consumerInfo, err := consumer.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	if consumerInfo.Config.AckPolicy != jetstream.AckExplicitPolicy || !reflect.DeepEqual(consumerInfo.Config.FilterSubjects, []string{"grp.build.msg.all.*", "grp.build.msg.dm.alice.*"}) {
		t.Fatalf("consumer config %+v", consumerInfo.Config)
	}
	if _, err := js.Stream(t.Context(), "GROUP_OTHER"); err == nil {
		t.Fatal("build account reached other group's stream")
	}
}

func TestAgentCannotUseBrokerRepliesAsAnotherSender(t *testing.T) {
	broker := testBus(t)
	operator := connectTest(t, broker, "build", "operator")
	alice := connectTest(t, broker, "build", "alice")
	for _, reply := range bobReplySubjects() {
		t.Run(reply, func(t *testing.T) {
			sub := subscribeReply(t, operator.conn, reply)
			defer func() {
				if err := sub.Unsubscribe(); err != nil {
					t.Error(err)
				}
			}()
			checkStreamReplies(t, alice, sub, reply)
			checkAPIRouteReplies(t, alice, sub, reply)
		})
	}
}

func checkStreamReplies(t *testing.T, alice testClient, sub *nats.Subscription, reply string) {
	t.Helper()
	for _, subject := range []string{
		"grp.build.msg.all.alice",
		"grp.build.msg.dm.bob.alice",
		"grp.build.msg.op.alice",
		"grp.build.evt.ready.alice",
	} {
		publishRequestDenied(t, alice, subject, reply, []byte("probe"))
		if msg, err := sub.NextMsg(100 * time.Millisecond); err != nats.ErrTimeout {
			t.Fatalf("broker published as bob after %s: message=%v error=%v", subject, msg, err)
		}
	}
}

func checkAPIRouteReplies(t *testing.T, alice testClient, sub *nats.Subscription, reply string) {
	t.Helper()
	for _, route := range []string{
		"$JS.API.INFO",
		"$JS.API.STREAM.CREATE.GROUP_BUILD",
		"$JS.API.STREAM.UPDATE.GROUP_BUILD",
		"$JS.API.STREAM.NAMES",
		"$JS.API.STREAM.LIST",
		"$JS.API.STREAM.INFO.GROUP_BUILD",
		"$JS.API.STREAM.DELETE.GROUP_BUILD",
		"$JS.API.STREAM.PURGE.GROUP_BUILD",
		"$JS.API.STREAM.SNAPSHOT.GROUP_BUILD",
		"$JS.API.STREAM.RESTORE.GROUP_BUILD",
		"$JS.API.STREAM.MSG.DELETE.GROUP_BUILD",
		"$JS.API.STREAM.MSG.GET.GROUP_BUILD",
		"$JS.API.DIRECT.GET.GROUP_BUILD",
		"$JS.API.DIRECT.GET.GROUP_BUILD.grp.build.msg.all.alice",
		"$JS.API.CONSUMER.CREATE.GROUP_BUILD",
		"$JS.API.CONSUMER.CREATE.GROUP_BUILD.alice.grp.build.msg.all.alice",
		"$JS.API.CONSUMER.DURABLE.CREATE.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.NAMES.GROUP_BUILD",
		"$JS.API.CONSUMER.LIST.GROUP_BUILD",
		"$JS.API.CONSUMER.INFO.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.DELETE.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.PAUSE.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.RESET.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.UNPIN.GROUP_BUILD.alice",
		"$JS.API.STREAM.PEER.REMOVE.GROUP_BUILD",
		"$JS.API.STREAM.PEER.EVACUATE.GROUP_BUILD",
		"$JS.API.STREAM.CANCEL_MOVE.GROUP_BUILD",
		"$JS.API.STREAM.LEADER.STEPDOWN.GROUP_BUILD",
		"$JS.API.CONSUMER.LEADER.STEPDOWN.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.PEER.REMOVE.GROUP_BUILD.alice",
		"$JS.API.CONSUMER.PEER.EVACUATE.GROUP_BUILD.alice",
		"$JS.API.META.LEADER.STEPDOWN",
		"$JS.API.SERVER.REMOVE",
		"$JS.API.SERVER.EVACUATE",
		"$JS.API.META.RESCUE",
		"$JS.API.ACCOUNT.PURGE.build",
		"$JS.API.ACCOUNT.STREAM.MOVE.build.GROUP_BUILD",
		"$JS.API.ACCOUNT.STREAM.CANCEL_MOVE.build.GROUP_BUILD",
		"$JS.ACK.GROUP_BUILD.alice.1.1.1.1.1",
		"$JS.SNAPSHOT.ACK.GROUP_BUILD.1",
	} {
		publishRequestDenied(t, alice, route, reply, []byte("{}"))
		if msg, err := sub.NextMsg(25 * time.Millisecond); err != nats.ErrTimeout {
			t.Fatalf("route %s published as bob: message=%v error=%v", route, msg, err)
		}
	}
}

func bobReplySubjects() []string {
	return []string{
		"grp.build.msg.all.bob",
		"grp.build.msg.dm.alice.bob",
		"grp.build.msg.dm.bob.bob",
		"grp.build.msg.op.bob",
		"grp.build.evt.ready.bob",
	}
}

func publishRequestDenied(t *testing.T, client testClient, subject, reply string, data []byte) {
	t.Helper()
	if err := client.conn.PublishRequest(subject, reply, data); err != nil {
		t.Fatal(err)
	}
	if err := client.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	expectPermissionError(t, client.errs)
}

func subscribeReply(t *testing.T, conn *nats.Conn, reply string) *nats.Subscription {
	t.Helper()
	sub, err := conn.SubscribeSync(reply)
	if err != nil {
		t.Fatal(err)
	}
	if err := conn.Flush(); err != nil {
		t.Fatal(err)
	}
	return sub
}

func TestRestartKeepsCredentialsAndStream(t *testing.T) {
	state := t.TempDir()
	first := startSingleAgentBus(t, state)
	path, err := first.CredentialPath("build", "alice")
	if err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	publishAndAck(t, first)
	first.Close()
	second := startSingleAgentBus(t, state)
	t.Cleanup(second.Close)
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(before, after) {
		t.Fatal("credential changed across restart")
	}
	assertPersistedMessageAndAck(t, second)
}

func startSingleAgentBus(t *testing.T, state string) *Bus {
	t.Helper()
	broker, err := Start(t.Context(), Config{StateDir: state, Port: -1, Groups: []Group{{Name: "build", Agents: []string{"alice"}}}})
	if err != nil {
		t.Fatal(err)
	}
	return broker
}

func publishAndAck(t *testing.T, broker *Bus) {
	t.Helper()
	operator := connectTest(t, broker, "build", "operator")
	_, firstStream := openTestStream(t, broker)
	if err := operator.conn.Publish("grp.build.msg.all.alice", []byte("persisted")); err != nil {
		t.Fatal(err)
	}
	if err := operator.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	consumer, err := firstStream.Consumer(t.Context(), "alice")
	if err != nil {
		t.Fatal(err)
	}
	batch, err := consumer.Fetch(1, jetstream.FetchMaxWait(time.Second))
	if err != nil {
		t.Fatal(err)
	}
	msg := <-batch.Messages()
	if msg == nil {
		t.Fatalf("fetch: %v", batch.Error())
	}
	if err := msg.DoubleAck(t.Context()); err != nil {
		t.Fatal(err)
	}
}

func assertPersistedMessageAndAck(t *testing.T, broker *Bus) {
	t.Helper()
	_, stream := openTestStream(t, broker)
	saved, err := stream.GetMsg(t.Context(), 1)
	if err != nil || string(saved.Data) != "persisted" {
		t.Fatalf("saved message: %v, %v", saved, err)
	}
	consumer, err := stream.Consumer(t.Context(), "alice")
	if err != nil {
		t.Fatal(err)
	}
	info, err := consumer.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	if info.AckFloor.Stream != 1 || info.NumAckPending != 0 {
		t.Fatalf("consumer progress after restart: %+v", info)
	}
}

func openTestStream(t *testing.T, broker *Bus) (jetstream.JetStream, jetstream.Stream) {
	t.Helper()
	operator := connectTest(t, broker, "build", "operator")
	js, err := jetstream.New(operator.conn)
	if err != nil {
		t.Fatal(err)
	}
	stream, err := js.Stream(t.Context(), "GROUP_BUILD")
	if err != nil {
		t.Fatal(err)
	}
	return js, stream
}
