package agentctl

import (
	"encoding/json/jsontext"
	"encoding/json/v2"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestParse(t *testing.T) {
	defaults := Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/alice.seed"}
	for _, test := range []struct {
		name string
		args []string
		ok   bool
	}{
		{"send", []string{"send", "bob", "hello", "--id", "same"}, true},
		{"broadcast", []string{"send", "*", "hello"}, true},
		{"receive", []string{"receive", "--timeout", "5"}, true},
		{"ack", []string{"ack", "opaque-token"}, true},
		{"foreign route", []string{"send", "Bad", "hello"}, false},
		{"empty text", []string{"send", "bob", ""}, false},
		{"invalid timeout", []string{"receive", "--timeout", "5000"}, false},
		{"unknown command", []string{"join"}, false},
		{"missing", nil, false},
		{"missing option value", []string{"send", "bob", "hi", "--group"}, false},
		{"unknown option", []string{"send", "bob", "hi", "--bad", "x"}, false},
		{"bad ID", []string{"send", "bob", "hi", "--id", "bad.id"}, false},
		{"ID on ack", []string{"ack", "token", "--id", "same"}, false},
		{"timeout on send", []string{"send", "bob", "hi", "--timeout", "1"}, false},
		{"short send", []string{"send", "bob"}, false},
		{"long text", []string{"send", "bob", strings.Repeat("x", 8193)}, false},
		{"text limit", []string{"send", "bob", strings.Repeat("x", 8192)}, true},
		{"missing ack token", []string{"ack"}, false},
		{"extra receive argument", []string{"receive", "extra"}, false},
		{"zero timeout", []string{"receive", "--timeout", "0"}, false},
		{"one timeout", []string{"receive", "--timeout", "1"}, true},
		{"max timeout", []string{"receive", "--timeout", "3600"}, true},
		{"bad port", []string{"receive", "--port", "65536"}, false},
		{"minimum port", []string{"receive", "--port", "1"}, true},
	} {
		t.Run(test.name, func(t *testing.T) {
			_, err := Parse(test.args, defaults)
			if (err == nil) != test.ok {
				t.Fatalf("parse error = %v", err)
			}
		})
	}
}

func TestParseIdentityAndOverrides(t *testing.T) {
	defaults := Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/alice.seed", Port: "4222"}
	cmd, err := Parse([]string{"receive", "--group", "other", "--agent", "bob", "--creds-file", "/tmp/bob.seed", "--port", "1234"}, defaults)
	if err != nil || cmd.Group != "other" || cmd.Agent != "bob" || cmd.CredsFile != "/tmp/bob.seed" || cmd.Port != 1234 {
		t.Fatalf("overrides = %+v, %v", cmd, err)
	}
	for _, test := range []struct {
		name     string
		defaults Defaults
	}{
		{"group", Defaults{Agent: "alice", CredsFile: "/tmp/file"}},
		{"agent", Defaults{Group: "build", CredsFile: "/tmp/file"}},
		{"file", Defaults{Group: "build", Agent: "alice"}},
		{"port", Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/file", Port: "bad"}},
	} {
		t.Run(test.name, func(t *testing.T) {
			if _, err := Parse([]string{"receive"}, test.defaults); err == nil {
				t.Fatal("accepted invalid defaults")
			}
		})
	}
}

func TestPayload(t *testing.T) {
	cmd := Command{Name: "send", Group: "build", Agent: "alice", To: "bob", Text: "hello"}
	request, err := Payload(cmd, "request", "same", 0)
	if err != nil || request.Destination != "dm" || request.To != "bob" || string(request.Envelope) != `{"body":{"text":"hello"}}` {
		t.Fatalf("payload = %+v, %v", request, err)
	}
	for _, test := range []struct{ to, destination string }{{"*", "all"}, {"operator", "operator"}} {
		cmd.To = test.to
		request, err := Payload(cmd, "request", "same", 0)
		if err != nil || request.Destination != test.destination || request.To != "" {
			t.Fatalf("route %s = %+v, %v", test.to, request, err)
		}
	}
	request, err = Payload(Command{Name: "receive"}, "request", "", 300)
	if err != nil || request.TimeoutMS != 300 {
		t.Fatalf("receive payload = %+v, %v", request, err)
	}
	request, err = Payload(Command{Name: "ack", ID: "opaque"}, "request", "", 0)
	if err != nil || request.Token != "opaque" {
		t.Fatalf("ack payload = %+v, %v", request, err)
	}
}

func TestPayloadTextProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		text := rapid.StringMatching(`[a-zA-Z0-9]{1,64}`).Draw(t, "text")
		cmd, err := Parse([]string{"send", "bob", text}, Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/alice.seed"})
		if err != nil {
			t.Fatal(err)
		}
		request, err := Payload(cmd, "request", "same", 0)
		var decoded struct {
			Body struct {
				Text string `json:"text"`
			} `json:"body"`
		}
		if err != nil || json.Unmarshal(request.Envelope, &decoded) != nil || decoded.Body.Text != text {
			t.Fatalf("round trip = %+v, %v", decoded, err)
		}
	})
}

func TestInterpretSend(t *testing.T) {
	cmd := Command{Name: "send", To: "bob"}
	for _, result := range []string{"stored", "duplicate"} {
		output, code := Interpret(cmd, Response{Result: result, Sequence: 7}, "same")
		if code != 0 || !output.OK || output.ID != "same" || output.Sequence != 7 {
			t.Fatalf("send %s = %+v, %d", result, output, code)
		}
	}
}

func TestInterpretReceiveAck(t *testing.T) {
	receive := Command{Name: "receive"}
	output, code := Interpret(receive, Response{Result: "delivered", Subject: "grp.build.msg.dm.bob.alice", Token: "opaque", Envelope: jsontext.Value(`{"body":{"text":"hello"}}`)}, "")
	if code != 0 || output.From != "alice" || output.ID != "opaque" {
		t.Fatalf("delivery = %+v, %d", output, code)
	}
	if _, code := Interpret(receive, Response{Result: "empty"}, ""); code != 3 {
		t.Fatalf("empty exit = %d", code)
	}
	if _, code := Interpret(Command{Name: "ack"}, Response{Result: "unknown-token"}, ""); code != 1 {
		t.Fatalf("foreign token exit = %d", code)
	}
	ack, code := Interpret(Command{Name: "ack", ID: "opaque"}, Response{Result: "acked"}, "")
	if code != 0 || ack.ID != "opaque" {
		t.Fatalf("ack = %+v, %d", ack, code)
	}
	if _, code := Interpret(receive, Response{Result: "delivered"}, ""); code != 1 {
		t.Fatalf("invalid delivery exit = %d", code)
	}
	if WaitMS(8000) != 5000 || WaitMS(2) != 2 || WaitMS(0) != 1 {
		t.Fatal("invalid receive wait")
	}
}

func TestSender(t *testing.T) {
	for _, test := range []struct{ subject, want string }{
		{"grp.build.msg.dm.bob.alice", "alice"},
		{"grp.build.msg.all.alice", "alice"},
		{"grp.build.msg.op.alice", "alice"},
		{"grp.build.relay.reply.bob.request", ""},
		{"grp.build.msg.dm.bob", ""},
	} {
		if got := Sender(test.subject); got != test.want {
			t.Fatalf("Sender(%q) = %q", test.subject, got)
		}
	}
}
