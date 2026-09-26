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
	if err := alice.conn.Publish("grp.build.msg.all.alice", []byte("allowed")); err != nil {
		t.Fatal(err)
	}
	if err := alice.conn.Flush(); err != nil {
		t.Fatal(err)
	}
	if _, err := allowed.NextMsg(time.Second); err != nil {
		t.Fatalf("own publication not delivered: %v", err)
	}
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
	operator := connectTest(t, broker, "build", "operator")
	js, err := jetstream.New(operator.conn)
	if err != nil {
		t.Fatal(err)
	}
	stream, err := js.Stream(t.Context(), "GROUP_BUILD")
	if err != nil {
		t.Fatal(err)
	}
	info, err := stream.Info(t.Context())
	if err != nil {
		t.Fatal(err)
	}
	if info.Config.Storage != jetstream.FileStorage || info.Config.Retention != jetstream.LimitsPolicy || !reflect.DeepEqual(info.Config.Subjects, []string{"grp.build.msg.>", "grp.build.evt.>"}) {
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
