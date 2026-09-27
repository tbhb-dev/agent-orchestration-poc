package perms

import (
	"reflect"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestAgent(t *testing.T) {
	got, err := Agent("build", "alice")
	want := Permissions{
		Publish: SubjectPermissions{Allow: []string{
			"grp.build.relay.req.send.alice", "grp.build.relay.req.receive.alice", "grp.build.relay.req.ack.alice", "grp.build.relay.req.status.alice", "grp.build.relay.req.roster.alice",
		}},
		Subscribe: SubjectPermissions{Allow: []string{"grp.build.relay.reply.alice.>"}},
	}
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("Agent = %+v, %v", got, err)
	}
	for _, tc := range []struct{ group, agent string }{{"bad.group", "alice"}, {"build", "bad.agent"}, {"build", "operator"}} {
		if _, err := Agent(tc.group, tc.agent); err == nil {
			t.Fatalf("Agent(%q, %q) accepted", tc.group, tc.agent)
		}
	}
}

func TestOperator(t *testing.T) {
	got, err := Operator("build")
	want := Permissions{
		Publish:   SubjectPermissions{Allow: []string{"grp.build.msg.>", "grp.build.evt.>", "grp.build.relay.reply.>", "$KV.>", "$JS.API.>", "$JS.ACK.>"}},
		Subscribe: SubjectPermissions{Allow: []string{"grp.build.msg.>", "grp.build.relay.req.>", "grp.build.evt.>", "_INBOX.>"}},
	}
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("Operator = %+v, %v", got, err)
	}
	if _, err := Operator("bad.group"); err == nil {
		t.Fatal("accepted invalid group")
	}
}

func TestPermissionProperties(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		group := rapid.StringMatching("[a-z][a-z0-9-]{0,8}").Draw(t, "group")
		agent := rapid.StringMatching("[a-z][a-z0-9-]{0,8}").Draw(t, "agent")
		p, err := Agent(group, agent)
		if err != nil || len(p.Publish.Allow) != 5 || len(p.Subscribe.Allow) != 1 {
			t.Fatalf("Agent = %+v, %v", p, err)
		}
		for _, subject := range p.Publish.Allow {
			if !strings.HasSuffix(subject, "."+agent) || !strings.HasPrefix(subject, "grp."+group+".") || strings.Contains(subject, ".msg.") {
				t.Fatalf("unsafe publish pattern %q", subject)
			}
		}
		op, err := Operator(group)
		if err != nil || len(op.Publish.Allow) != 6 || op.Publish.Allow[0] != "grp."+group+".msg.>" {
			t.Fatalf("Operator = %+v, %v", op, err)
		}
	})
}
