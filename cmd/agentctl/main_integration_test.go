//go:build integration

package main

import (
	"bytes"
	"encoding/json/v2"
	"net/url"
	"strconv"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/bus"
	"github.com/tbhb/agent-orchestration-poc/internal/core/agentctl"
)

func TestRelayCLIExchange(t *testing.T) {
	broker, err := bus.Start(t.Context(), bus.Config{StateDir: t.TempDir(), Port: -1, Groups: []bus.Group{{Name: "build", Agents: []string{"alice", "bob"}}}})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(broker.Close)
	address, err := url.Parse(broker.URL())
	if err != nil {
		t.Fatal(err)
	}
	port := address.Port()
	call := func(agent string, args ...string) (agentctl.Output, int) {
		t.Helper()
		path, pathErr := broker.CredentialPath("build", agent)
		if pathErr != nil {
			t.Fatal(pathErr)
		}
		args = append(args, "--group", "build", "--agent", agent, "--creds-file", path, "--port", port)
		var output bytes.Buffer
		code := run(args, &output)
		t.Logf("%s %s: %s", agent, args[0], bytes.TrimSpace(output.Bytes()))
		var result agentctl.Output
		if err := json.Unmarshal(output.Bytes(), &result); err != nil {
			t.Fatalf("output %q: %v", output.String(), err)
		}
		return result, code
	}
	first, code := call("alice", "send", "bob", "hello", "--id", "same")
	if code != 0 || first.Result != "stored" || first.Sequence == 0 {
		t.Fatalf("first send = %+v, %d", first, code)
	}
	second, code := call("alice", "send", "bob", "hello", "--id", "same")
	if code != 0 || second.Result != "duplicate" || second.Sequence != first.Sequence {
		t.Fatalf("duplicate send = %+v, %d", second, code)
	}
	delivery, code := call("bob", "receive", "--timeout", "1")
	if code != 0 || delivery.ID == "" || delivery.From != "alice" || string(delivery.Message) != `{"body":{"text":"hello"}}` {
		t.Fatalf("delivery = %+v, %d", delivery, code)
	}
	ack, code := call("bob", "ack", delivery.ID)
	if code != 0 || ack.Result != "acked" {
		t.Fatalf("ack = %+v, %d", ack, code)
	}
	again, code := call("bob", "ack", delivery.ID)
	if code != 1 || again.Result != "unknown-token" {
		t.Fatalf("reused token = %+v, %d", again, code)
	}
	empty, code := call("bob", "receive", "--timeout", strconv.Itoa(1))
	if code != 3 || empty.Result != "empty" {
		t.Fatalf("empty = %+v, %d", empty, code)
	}
	t.Log("stored, duplicate, delivered, acked, reused token rejected, empty timeout")
}
