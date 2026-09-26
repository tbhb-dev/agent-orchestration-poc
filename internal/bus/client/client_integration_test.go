//go:build integration

package client

import (
	"context"
	"errors"
	"net/url"
	"strconv"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"github.com/tbhb/agent-orchestration-poc/internal/bus"
	"github.com/tbhb/agent-orchestration-poc/internal/core/command"
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

type testPair struct {
	alice *Client
	bob   *Client
}

func startTestPair(t *testing.T) testPair {
	t.Helper()
	broker, err := bus.Start(t.Context(), bus.Config{StateDir: t.TempDir(), Port: -1, Groups: []bus.Group{{Name: "build", Agents: []string{"alice", "bob"}}}})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(broker.Close)
	parsed, err := url.Parse(broker.URL())
	if err != nil {
		t.Fatal(err)
	}
	port, err := strconv.Atoi(parsed.Port())
	if err != nil {
		t.Fatal(err)
	}
	connect := func(agent string) *Client {
		t.Helper()
		path, err := broker.CredentialPath("build", agent)
		if err != nil {
			t.Fatal(err)
		}
		client, err := Connect(command.Value{Group: "build", Agent: agent, CredsFile: path, Port: port})
		if err != nil {
			t.Fatal(err)
		}
		t.Cleanup(client.Close)
		return client
	}
	operatorPath, err := broker.CredentialPath("build", "operator")
	if err != nil {
		t.Fatal(err)
	}
	option, err := nats.NkeyOptionFromSeed(operatorPath)
	if err != nil {
		t.Fatal(err)
	}
	operator, err := nats.Connect(broker.URL(), option)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(operator.Close)
	js, err := jetstream.New(operator)
	if err != nil {
		t.Fatal(err)
	}
	stream, err := layout.Stream("build")
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"alice", "bob"} {
		consumer, err := layout.Consumer("build", name)
		if err != nil {
			t.Fatal(err)
		}
		_, err = js.UpdateConsumer(t.Context(), stream.Name, jetstream.ConsumerConfig{
			Name: consumer.Name, Durable: consumer.Name, FilterSubjects: consumer.FilterSubjects,
			AckPolicy: jetstream.AckExplicitPolicy, AckWait: 200 * time.Millisecond,
		})
		if err != nil {
			t.Fatal(err)
		}
	}
	return testPair{alice: connect("alice"), bob: connect("bob")}
}

func testValue(agent, name string) command.Value {
	return command.Value{Group: "build", Agent: agent, Name: name, Timeout: time.Second}
}

func TestSendReceiveAckAndDedup(t *testing.T) {
	clients := startTestPair(t)
	send := testValue("alice", "send")
	send.To, send.Text, send.ID = "bob", "hello", "dedup-1"
	if _, err := clients.alice.Run(t.Context(), send); err != nil {
		t.Fatal(err)
	}
	if _, err := clients.alice.Run(t.Context(), send); err != nil {
		t.Fatal(err)
	}
	received, err := clients.bob.Run(t.Context(), testValue("bob", "receive"))
	if err != nil || received.Message.Body.Text != "hello" {
		t.Fatalf("receive = %#v, %v", received, err)
	}
	ack := testValue("bob", "ack")
	ack.ID = received.ID
	if _, err := clients.bob.Run(t.Context(), ack); err != nil {
		t.Fatal(err)
	}
	timeout := testValue("bob", "receive")
	timeout.Timeout = 300 * time.Millisecond
	if _, err := clients.bob.Run(t.Context(), timeout); !errors.Is(err, ErrTimeout) {
		t.Fatalf("deduplicated receive = %v", err)
	}
}

func TestRedeliveryAndReceiveTimeout(t *testing.T) {
	clients := startTestPair(t)
	value := testValue("bob", "receive")
	value.Timeout = 300 * time.Millisecond
	if _, err := clients.bob.Run(t.Context(), value); !errors.Is(err, ErrTimeout) {
		t.Fatalf("empty receive = %v", err)
	}
	send := testValue("alice", "send")
	send.To, send.Text = "bob", "redeliver"
	if _, err := clients.alice.Run(t.Context(), send); err != nil {
		t.Fatal(err)
	}
	first, err := clients.bob.Run(t.Context(), value)
	if err != nil {
		t.Fatal(err)
	}
	time.Sleep(250 * time.Millisecond)
	second, err := clients.bob.Run(t.Context(), value)
	if err != nil || first.Message.Headers.ID != second.Message.Headers.ID {
		t.Fatalf("redelivery = %#v, %v", second, err)
	}
	ack := testValue("bob", "ack")
	ack.ID = second.ID
	if _, err := clients.bob.Run(t.Context(), ack); err != nil {
		t.Fatal(err)
	}
}

func TestSendWaitLeavesReplyForReceive(t *testing.T) {
	clients := startTestPair(t)
	answer := make(chan error, 1)
	go func() {
		question := testValue("alice", "send")
		question.To, question.Text, question.Wait = "bob", "question", 2*time.Second
		result, err := clients.alice.Run(context.Background(), question)
		if err == nil && result.Message.Body.Text != "answer" {
			err = errors.New("wrong answer")
		}
		answer <- err
	}()
	question, err := clients.bob.Run(t.Context(), testValue("bob", "receive"))
	if err != nil {
		t.Fatal(err)
	}
	ack := testValue("bob", "ack")
	ack.ID = question.ID
	if _, err := clients.bob.Run(t.Context(), ack); err != nil {
		t.Fatal(err)
	}
	receive := make(chan error, 1)
	go func() {
		result, err := clients.alice.Run(context.Background(), testValue("alice", "receive"))
		if err == nil && result.Message.Body.Text != "answer" {
			err = errors.New("receive missed answer")
		}
		receive <- err
	}()
	reply := testValue("bob", "send")
	reply.To, reply.Text = "alice", "answer"
	reply.CorrelationID = question.Message.Headers.ID
	reply.ReplyToID = question.Message.Headers.ID
	if _, err := clients.bob.Run(t.Context(), reply); err != nil {
		t.Fatal(err)
	}
	if err := <-answer; err != nil {
		t.Fatal(err)
	}
	if err := <-receive; err != nil {
		t.Fatal(err)
	}
}

func TestJoinStatusAndRoster(t *testing.T) {
	clients := startTestPair(t)
	if _, err := clients.alice.Run(t.Context(), testValue("alice", "join")); err != nil {
		t.Fatal(err)
	}
	if _, err := clients.bob.Run(t.Context(), testValue("bob", "join")); err != nil {
		t.Fatal(err)
	}
	status := testValue("alice", "status")
	status.Set, status.Detail = "working", "reviewing"
	result, err := clients.alice.Run(t.Context(), status)
	if err != nil || result.Status != "working" || result.Detail != "reviewing" {
		t.Fatalf("status = %#v, %v", result, err)
	}
	roster, err := clients.bob.Run(t.Context(), testValue("bob", "roster"))
	if err != nil || len(roster.Roster) != 2 {
		t.Fatalf("roster = %#v, %v", roster, err)
	}
}
