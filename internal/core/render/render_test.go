package render

import (
	"bytes"
	"encoding/json/v2"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/state"
	"pgregory.net/rapid"
)

func TestRender(t *testing.T) {
	for _, tc := range []struct {
		name string
		in   Result
	}{
		{"sent", Result{OK: true, Command: "send", ID: "msg-1", To: "bob"}},
		{"timeout", Result{OK: false, Command: "receive", Error: "timeout"}},
		{"roster", Result{OK: true, Command: "roster", Roster: map[string]state.Roster{"alice": {Role: "worker", JoinedAt: "now"}}}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			body, summary, err := Render(tc.in)
			if err != nil || summary == "" || !bytes.HasSuffix(body, []byte("\n")) {
				t.Fatalf("Render = %q, %q, %v", body, summary, err)
			}
			var decoded Result
			if err := json.Unmarshal(bytes.TrimSpace(body), &decoded); err != nil || decoded.Command != tc.in.Command || decoded.OK != tc.in.OK {
				t.Fatalf("decoded = %#v, %v", decoded, err)
			}
		})
	}
}

func TestRenderProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		id := rapid.StringMatching(`[a-z0-9]{1,30}`).Draw(t, "id")
		body, _, err := Render(Result{OK: true, Command: "ack", ID: id})
		if err != nil {
			t.Fatal(err)
		}
		var got map[string]any
		if err := json.Unmarshal(body, &got); err != nil || got["id"] != id {
			t.Fatalf("Render = %q, %v", body, err)
		}
	})
}
