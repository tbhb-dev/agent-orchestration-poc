package layout

import (
	"reflect"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestValidToken(t *testing.T) {
	for _, tc := range []struct {
		name string
		want bool
	}{
		{"build", true},
		{"worker-1", true},
		{"a_b", true},
		{"", false},
		{"1worker", false},
		{"a.b", false},
		{"a*", false},
		{"a>", false},
		{"a b", false},
		{"A", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if (ValidToken(tc.name) == nil) != tc.want {
				t.Fatalf("ValidToken(%q) validity != %t", tc.name, tc.want)
			}
		})
	}
}

func TestSubjectsAndStream(t *testing.T) {
	for _, tc := range []struct {
		name string
		call func() (string, error)
		want string
	}{
		{"broadcast", func() (string, error) { return Broadcast("build", "alice") }, "grp.build.msg.all.alice"},
		{"direct", func() (string, error) { return Direct("build", "bob", "alice") }, "grp.build.msg.dm.bob.alice"},
		{"operator", func() (string, error) { return Operator("build", "alice") }, "grp.build.msg.op.alice"},
		{"event", func() (string, error) { return Event("build", "blocked", "alice") }, "grp.build.evt.blocked.alice"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := tc.call()
			if err != nil || got != tc.want {
				t.Fatalf("got %q, %v; want %q", got, err, tc.want)
			}
		})
	}
	for _, tc := range []struct {
		name string
		call func() error
	}{
		{"broadcast", func() error { _, err := Broadcast("bad.group", "alice"); return err }},
		{"direct", func() error { _, err := Direct("build", "bob", "bad.agent"); return err }},
		{"operator", func() error { _, err := Operator("build", "a b"); return err }},
		{"event", func() error { _, err := Event("build", "a.b", "alice"); return err }},
		{"stream", func() error { _, err := Stream("a.b"); return err }},
		{"filters", func() error { _, err := ConsumerFilters("build", "a.b"); return err }},
	} {
		t.Run("invalid-"+tc.name, func(t *testing.T) {
			if err := tc.call(); err == nil {
				t.Fatal("accepted invalid token")
			}
		})
	}
	stream, err := Stream("build")
	if err != nil || stream.Name != "GROUP_BUILD" || !reflect.DeepEqual(stream.Subjects, []string{"grp.build.msg.>", "grp.build.evt.>"}) {
		t.Fatalf("stream = %+v, %v", stream, err)
	}
	filters, err := ConsumerFilters("build", "alice")
	if err != nil || !reflect.DeepEqual(filters, []string{"grp.build.msg.all.*", "grp.build.msg.dm.alice.*"}) {
		t.Fatalf("filters = %v, %v", filters, err)
	}
}

func TestProperties(t *testing.T) {
	valid := rapid.Custom(func(t *rapid.T) string {
		first := rapid.StringMatching("[a-z]").Draw(t, "first")
		rest := rapid.StringMatching("[a-z0-9_-]{0,12}").Draw(t, "rest")
		return first + rest
	})
	rapid.Check(t, func(t *rapid.T) {
		group := valid.Draw(t, "group")
		agent := valid.Draw(t, "agent")
		to := valid.Draw(t, "to")
		kind := valid.Draw(t, "kind")
		if err := ValidToken(group); err != nil {
			t.Fatal(err)
		}
		for _, build := range []func() (string, error){
			func() (string, error) { return Broadcast(group, agent) },
			func() (string, error) { return Direct(group, to, agent) },
			func() (string, error) { return Operator(group, agent) },
			func() (string, error) { return Event(group, kind, agent) },
		} {
			subject, err := build()
			if err != nil || !strings.HasPrefix(subject, "grp."+group+".") || !strings.HasSuffix(subject, "."+agent) {
				t.Fatalf("subject %q: %v", subject, err)
			}
		}
		stream, err := Stream(group)
		if err != nil || len(stream.Subjects) != 2 || stream.Subjects[0] != "grp."+group+".msg.>" || stream.Subjects[1] != "grp."+group+".evt.>" {
			t.Fatalf("stream %+v: %v", stream, err)
		}
		filters, err := ConsumerFilters(group, agent)
		if err != nil || len(filters) != 2 || filters[1] != "grp."+group+".msg.dm."+agent+".*" {
			t.Fatalf("filters %v: %v", filters, err)
		}
	})
}

func TestInvalidProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		name := rapid.StringMatching("[a-z][a-z0-9_-]{0,8}").Draw(t, "name")
		if ValidToken(name+".other") == nil {
			t.Fatal("accepted multiple tokens")
		}
	})
}
