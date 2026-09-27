package relay

import (
	"encoding/json/jsontext"
	"encoding/json/v2"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestParseRequest(t *testing.T) {
	for _, subject := range []string{
		"grp.build.relay.req.send.alice", "grp.build.relay.req.receive.alice",
		"grp.build.relay.req.ack.alice", "grp.build.relay.req.status.alice", "grp.build.relay.req.roster.alice",
	} {
		got, err := ParseRequest("build", subject)
		if err != nil || got.Group != "build" || got.Agent != "alice" {
			t.Fatalf("ParseRequest(%q) = %+v, %v", subject, got, err)
		}
	}
	for _, subject := range []string{"grp.other.relay.req.send.alice", "grp.build.relay.req.send.bob.more", "grp.build.relay.reply.alice.x", "grp.build.relay.req.bogus.alice", "grp.build.relay.req.send.operator", "grp.build.relay.req.send.a*"} {
		if _, err := ParseRequest("build", subject); err == nil {
			t.Fatalf("accepted %q", subject)
		}
	}
}

func TestReplyAndSendSubject(t *testing.T) {
	req := Request{Group: "build", Agent: "alice"}
	reply, err := Reply(req, "request-1")
	if err != nil || reply != "grp.build.relay.reply.alice.request-1" {
		t.Fatalf("Reply = %q, %v", reply, err)
	}
	if _, err := Reply(req, "bad.id"); err == nil {
		t.Fatal("accepted invalid request id")
	}
	for _, tc := range []struct{ destination, to, want string }{
		{"all", "", "grp.build.msg.all.alice"},
		{"dm", "bob", "grp.build.msg.dm.bob.alice"},
		{"operator", "", "grp.build.msg.op.alice"},
	} {
		got, err := SendSubject(req, tc.destination, tc.to)
		if err != nil || got != tc.want {
			t.Fatalf("SendSubject(%q, %q) = %q, %v", tc.destination, tc.to, got, err)
		}
	}
	for _, tc := range []struct{ destination, to string }{{"all", "bob"}, {"dm", "bad.name"}, {"operator", "bob"}, {"unknown", ""}} {
		if _, err := SendSubject(req, tc.destination, tc.to); err == nil {
			t.Fatalf("accepted %+v", tc)
		}
	}
}

func TestMessageIDAndEnvelope(t *testing.T) {
	alice := Request{Group: "build", Agent: "alice"}
	base, err := MessageID(alice, "grp.build.msg.all.alice", "same")
	if err != nil || base == "" {
		t.Fatalf("MessageID = %q, %v", base, err)
	}
	for _, tc := range []struct {
		req     Request
		subject string
	}{
		{Request{Group: "build", Agent: "bob"}, "grp.build.msg.all.bob"},
		{alice, "grp.build.msg.dm.bob.alice"},
	} {
		got, err := MessageID(tc.req, tc.subject, "same")
		if err != nil || got == base {
			t.Fatalf("id collision: %q, %v", got, err)
		}
	}
	if _, err := MessageID(alice, "grp.build.msg.all.bob", "same"); err == nil {
		t.Fatal("accepted foreign sender")
	}
	for _, tc := range []struct {
		value string
		valid bool
	}{{`{"body":"hi"}`, true}, {`[]`, false}, {`{`, false}, {`null`, false}} {
		if ValidEnvelope(jsontext.Value(tc.value)) != tc.valid {
			t.Fatalf("ValidEnvelope(%q)", tc.value)
		}
	}
}

func TestOwns(t *testing.T) {
	d := Delivery{Group: "build", Agent: "alice", Consumer: "alice", Sequence: 3, Generation: 2}
	if !Owns(d, Request{Group: "build", Agent: "alice"}, "alice", 3, 2) {
		t.Fatal("owner rejected")
	}
	for _, tc := range []struct {
		req             Request
		consumer        string
		seq, generation uint64
	}{
		{Request{Group: "build", Agent: "bob"}, "alice", 3, 2},
		{Request{Group: "other", Agent: "alice"}, "alice", 3, 2},
		{Request{Group: "build", Agent: "alice"}, "bob", 3, 2},
		{Request{Group: "build", Agent: "alice"}, "alice", 4, 2},
		{Request{Group: "build", Agent: "alice"}, "alice", 3, 3},
	} {
		if Owns(d, tc.req, tc.consumer, tc.seq, tc.generation) {
			t.Fatalf("accepted %+v", tc)
		}
	}
}

func TestRelaySubjectProperty(t *testing.T) {
	t.Run("subject identity", rapid.MakeCheck(func(t *rapid.T) {
		group := rapid.StringMatching("[a-z][a-z0-9-]{0,8}").Draw(t, "group")
		agent := rapid.StringMatching("[a-z][a-z0-9-]{0,8}").Draw(t, "agent")
		if agent == "operator" {
			return
		}
		req, err := ParseRequest(group, "grp."+group+".relay.req.send."+agent)
		if err != nil {
			t.Fatal(err)
		}
		reply, err := Reply(req, "request")
		if err != nil || !strings.HasPrefix(reply, "grp."+group+".relay.reply."+agent+".") {
			t.Fatalf("reply %q, %v", reply, err)
		}
		subject, err := SendSubject(req, "all", "")
		if err != nil || !strings.HasSuffix(subject, "."+agent) {
			t.Fatalf("subject %q, %v", subject, err)
		}
		id, err := MessageID(req, subject, "same")
		if err != nil || id == "" {
			t.Fatalf("id %q, %v", id, err)
		}
		other := req
		other.Agent = agent + "x"
		otherSubject, _ := SendSubject(other, "all", "")
		otherID, _ := MessageID(other, otherSubject, "same")
		if id == otherID {
			t.Fatal("identity collision")
		}
	}))
}

func TestEnvelopeProperty(t *testing.T) {
	t.Run("envelope", rapid.MakeCheck(func(t *rapid.T) {
		body := rapid.String().Draw(t, "body")
		value, err := json.Marshal(map[string]string{"body": body})
		if err != nil {
			t.Fatal(err)
		}
		if len(value) <= 64*1024 && !ValidEnvelope(jsontext.Value(value)) {
			t.Fatal("valid object rejected")
		}
		if ValidEnvelope(jsontext.Value(append(value, '!'))) {
			t.Fatal("trailing invalid byte accepted")
		}
	}))
}

func TestDeliveryOwnerProperty(t *testing.T) {
	t.Run("delivery owner", rapid.MakeCheck(func(t *rapid.T) {
		sequence := rapid.Uint64Range(1, 1000).Draw(t, "sequence")
		generation := rapid.Uint64Range(1, 1000).Draw(t, "generation")
		d := Delivery{Group: "build", Agent: "alice", Consumer: "alice", Sequence: sequence, Generation: generation}
		req := Request{Group: "build", Agent: "alice"}
		if !Owns(d, req, "alice", sequence, generation) || Owns(d, req, "alice", sequence+1, generation) || Owns(d, req, "alice", sequence, generation+1) {
			t.Fatal("delivery binding changed")
		}
	}))
}
