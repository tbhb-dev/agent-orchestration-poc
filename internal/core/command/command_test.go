package command

import (
	"testing"
	"time"

	"pgregory.net/rapid"
)

func TestParse(t *testing.T) {
	for _, tc := range []struct {
		name string
		args []string
		want Value
		err  bool
	}{
		{"send", []string{"send", "bob", "hello", "--wait", "4"}, Value{Name: "send", To: "bob", Text: "hello", Wait: 4 * time.Second, Timeout: 30 * time.Second, Port: 4222}, false},
		{"receive", []string{"receive", "--timeout", "2"}, Value{Name: "receive", Timeout: 2 * time.Second, Port: 4222}, false},
		{"ack", []string{"ack", "msg-1"}, Value{Name: "ack", ID: "msg-1", Timeout: 30 * time.Second, Port: 4222}, false},
		{"roster", []string{"roster"}, Value{Name: "roster", Timeout: 30 * time.Second, Port: 4222}, false},
		{"no command", nil, Value{}, true},
		{"bad recipient", []string{"send", "Bad", "hi"}, Value{}, true},
		{"bad wait", []string{"send", "bob", "hi", "--wait", "0"}, Value{}, true},
		{"missing flag value", []string{"receive", "--timeout"}, Value{}, true},
		{"bad status", []string{"status", "--set", "away"}, Value{}, true},
		{"detail alone", []string{"status", "--detail", "hello"}, Value{}, true},
		{"extra args", []string{"join", "x"}, Value{}, true},
		{"unknown", []string{"memory"}, Value{}, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := Parse(tc.args)
			if (err != nil) != tc.err {
				t.Fatalf("error = %v", err)
			}
			if !tc.err && got != tc.want {
				t.Fatalf("got %#v, want %#v", got, tc.want)
			}
		})
	}
}

func TestResolve(t *testing.T) {
	base, err := Parse([]string{"join"})
	if err != nil {
		t.Fatal(err)
	}
	got, err := Resolve(base, Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/alice.seed", Port: "1234"})
	if err != nil || got.Group != "build" || got.Agent != "alice" || got.Port != 1234 || got.CredsFile != "/tmp/alice.seed" {
		t.Fatalf("Resolve = %#v, %v", got, err)
	}
	for _, defaults := range []Defaults{
		{Group: "", Agent: "alice", CredsFile: "/tmp/file"},
		{Group: "build", Agent: "Bad", CredsFile: "/tmp/file"},
		{Group: "build", Agent: "alice", CredsFile: ""},
		{Group: "build", Agent: "alice", CredsFile: "/tmp/file", Port: "bad"},
	} {
		if _, err := Resolve(base, defaults); err == nil {
			t.Fatalf("accepted %#v", defaults)
		}
	}
	ack := Value{Name: "ack", ID: "$JS.ACK.GROUP_BUILD.bob.1", Port: 4222}
	if _, err := Resolve(ack, Defaults{Group: "build", Agent: "alice", CredsFile: "/tmp/file"}); err == nil {
		t.Fatal("accepted another agent's ack token")
	}
}

func TestSendTextProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		text := rapid.StringMatching(`[a-zA-Z0-9 ]{1,100}`).Draw(t, "text")
		got, err := Parse([]string{"send", "bob", text})
		if err != nil || got.Text != text || got.To != "bob" {
			t.Fatalf("Parse = %#v, %v", got, err)
		}
	})
}

func TestRoutesAndAckSubject(t *testing.T) {
	for _, tc := range []struct {
		to      string
		subject string
	}{
		{"bob", "grp.build.msg.dm.bob.alice"},
		{"*", "grp.build.msg.all.alice"},
		{"operator", "grp.build.msg.op.alice"},
	} {
		value := Value{Group: "build", Agent: "alice", To: tc.to}
		got, err := Subject(value)
		if err != nil || got != tc.subject || Sender(got) != "alice" {
			t.Fatalf("subject = %q, sender = %q, %v", got, Sender(got), err)
		}
	}
	value := Value{Group: "build", Agent: "alice"}
	if !ValidAckSubject(value, "$JS.ACK.GROUP_BUILD.alice.1.2.3") {
		t.Fatal("rejected own ack token")
	}
	for _, token := range []string{"$JS.ACK.GROUP_BUILD.bob.1.2.3", "$JS.ACK.GROUP_OTHER.alice.1.2.3", "garbage"} {
		if ValidAckSubject(value, token) {
			t.Fatalf("accepted %q", token)
		}
	}
	if Kind(Value{Wait: time.Second}) != "question" || Kind(Value{CorrelationID: "id"}) != "answer" || Kind(Value{}) != "message" {
		t.Fatal("wrong message kind")
	}
}

func TestJoinValuesAndReplyFilters(t *testing.T) {
	value := Value{Group: "build", Agent: "alice"}
	if Role(Value{Agent: "operator"}) != "operator" || Role(value) != "worker" || JoinInstructions() == "" {
		t.Fatal("wrong join values")
	}
	filter, err := ReplyFilter(value)
	if err != nil || filter != "grp.build.msg.dm.alice.*" {
		t.Fatalf("reply filter = %q, %v", filter, err)
	}
	filter, err = ReplyFilter(Value{Group: "build", Agent: "operator"})
	if err != nil || filter != "grp.build.msg.>" {
		t.Fatalf("operator reply filter = %q, %v", filter, err)
	}
}
