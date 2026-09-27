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

func TestClassifyPublish(t *testing.T) {
	for _, tc := range []struct {
		name     string
		ack      PublishAck
		want     string
		sequence uint64
	}{
		{"missing", PublishAck{}, "unknown", 0},
		{"wrong stream", PublishAck{Received: true, Stream: "OTHER", Sequence: 4}, "unknown", 0},
		{"zero sequence", PublishAck{Received: true, Stream: "GROUP_BUILD"}, "unknown", 0},
		{"stored", PublishAck{Received: true, Stream: "GROUP_BUILD", Sequence: 4}, "stored", 4},
		{"duplicate", PublishAck{Received: true, Stream: "GROUP_BUILD", Sequence: 4, Duplicate: true}, "duplicate", 4},
	} {
		t.Run(tc.name, func(t *testing.T) {
			result, sequence := ClassifyPublish("GROUP_BUILD", tc.ack)
			if result != tc.want || sequence != tc.sequence {
				t.Fatalf("got %s/%d, want %s/%d", result, sequence, tc.want, tc.sequence)
			}
		})
	}
}

func TestReceiveWait(t *testing.T) {
	for _, tc := range []struct {
		input, wait int
		valid       bool
	}{{-1, 0, false}, {0, 1000, true}, {1, 1, true}, {5000, 5000, true}, {5001, 0, false}} {
		wait, valid := ReceiveWait(tc.input)
		if wait != tc.wait || valid != tc.valid {
			t.Fatalf("ReceiveWait(%d) = %d/%v", tc.input, wait, valid)
		}
	}
}

func TestDeliveryTransitions(t *testing.T) {
	req := Request{Group: "build", Agent: "alice"}
	first, ok := DeliveryFromMetadata(req, "GROUP_BUILD", "GROUP_BUILD", "alice", 9, 1)
	if !ok || first.Sequence != 9 || first.Generation != 1 {
		t.Fatalf("first metadata: %+v/%v", first, ok)
	}
	for _, tc := range []struct {
		stream, consumer     string
		sequence, generation uint64
	}{
		{"OTHER", "alice", 9, 1},
		{"GROUP_BUILD", "bob", 9, 1},
		{"GROUP_BUILD", "alice", 0, 1},
		{"GROUP_BUILD", "alice", 9, 0},
	} {
		if _, valid := DeliveryFromMetadata(req, "GROUP_BUILD", tc.stream, tc.consumer, tc.sequence, tc.generation); valid {
			t.Fatalf("accepted metadata %+v", tc)
		}
	}
}

func TestTokenTransitions(t *testing.T) {
	req := Request{Group: "build", Agent: "alice"}
	first := Delivery{Group: "build", Agent: "alice", Consumer: "alice", Sequence: 9, Generation: 1}
	second := first
	second.Generation = 2
	if install, remove := PlanInstall(map[string]Delivery{"old": first}, second); !install || len(remove) != 1 || remove[0] != "old" {
		t.Fatalf("new generation: %v/%v", install, remove)
	}
	if install, remove := PlanInstall(map[string]Delivery{"new": second}, first); install || len(remove) != 0 {
		t.Fatalf("stale generation: %v/%v", install, remove)
	}
	if install, remove := PlanInstall(map[string]Delivery{"new": second}, second); install || len(remove) != 0 {
		t.Fatalf("same generation: %v/%v", install, remove)
	}
	if !CanConsume(second, true, req) || CanConsume(second, false, req) || CanConsume(second, true, Request{Group: "build", Agent: "bob"}) {
		t.Fatal("token ownership changed")
	}
}
