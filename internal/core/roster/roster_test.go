package roster

import (
	"path/filepath"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestBranch(t *testing.T) {
	cases := []struct {
		name, kind, slug, want string
		issue                  int
	}{
		{"feature", "feat", "registry-tmux", "feat/28-registry-tmux", 28},
		{"bad type", "other", "registry", "", 28},
		{"bad issue", "feat", "registry", "", 0},
		{"path escape", "feat", "../other", "", 28},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := Branch(tc.kind, tc.issue, tc.slug)
			if got != tc.want || (err != nil) != (tc.want == "") {
				t.Fatalf("Branch() = %q, %v, want %q", got, err, tc.want)
			}
		})
	}
}

func TestWorktree(t *testing.T) {
	got, err := Worktree("/repo", "feat/28-registry-tmux")
	if err != nil || got != filepath.Join("/repo", ".worktrees", "feat-28-registry-tmux") {
		t.Fatalf("Worktree() = %q, %v", got, err)
	}
	if _, err := Worktree("/repo", "../escape"); err == nil {
		t.Fatal("accepted path escape")
	}
}

func TestTransition(t *testing.T) {
	cases := []struct {
		from, to State
		valid    bool
	}{
		{Requested, Starting, true},
		{Starting, Running, true},
		{Running, Stopping, true},
		{Stopping, Stopped, true},
		{Running, Failed, true},
		{Stopped, Starting, true},
		{Requested, Running, false},
		{Stopped, Running, false},
		{Running, Running, false},
	}
	for _, tc := range cases {
		t.Run(string(tc.from)+"-"+string(tc.to), func(t *testing.T) {
			got, err := Transition(tc.from, tc.to)
			if (err == nil) != tc.valid || (tc.valid && got != tc.to) {
				t.Fatalf("Transition() = %q, %v", got, err)
			}
		})
	}
}

func TestValidateWorker(t *testing.T) {
	w := Worker{
		ID: "id", GroupID: "group", Name: "codex-impl", Harness: "codex", Model: "gpt-6-sol", Effort: "high", Issue: 28,
		Kind: "feat", Slug: "registry-tmux", Branch: "feat/28-registry-tmux", WorktreePath: "/repo/.worktrees/feat-28-registry-tmux", BriefPath: "/brief", CreatedAt: "2026-09-26T00:00:00Z",
	}
	if err := ValidateWorker(w); err != nil {
		t.Fatal(err)
	}
	w.Name = "operator"
	if err := ValidateWorker(w); err == nil {
		t.Fatal("accepted reserved name")
	}
}

func TestBranchProperties(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		issue := rapid.IntRange(1, 99999).Draw(t, "issue")
		slug := rapid.StringMatching("[a-z][a-z0-9-]{0,20}[a-z0-9]").Draw(t, "slug")
		branch, err := Branch("feat", issue, slug)
		if err != nil || !strings.HasPrefix(branch, "feat/") {
			t.Fatalf("invalid branch %q: %v", branch, err)
		}
		path, err := Worktree("/repo", branch)
		if err != nil || !strings.HasPrefix(path, "/repo/.worktrees/feat-") {
			t.Fatalf("invalid worktree %q: %v", path, err)
		}
	})
}

func TestSocketAndAgentNames(t *testing.T) {
	name, err := SocketName("/state/build")
	if err != nil || len(name) != 9 || name[0] != 'a' {
		t.Fatalf("SocketName() = %q, %v", name, err)
	}
	if _, err := SocketName("relative"); err == nil {
		t.Fatal("accepted relative state path")
	}
	got := AgentNames([]string{"first", "first"}, []Worker{{Name: "first"}, {Name: "second"}})
	if len(got) != 2 || got[0] != "first" || got[1] != "second" {
		t.Fatalf("AgentNames() = %v", got)
	}
}

func TestStateAndAgentProperties(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		state := rapid.SampledFrom([]State{Requested, Starting, Running, Stopping, Stopped, Failed}).Draw(t, "state")
		if _, err := Transition(state, state); err == nil {
			t.Fatalf("self transition accepted for %q", state)
		}
		name := rapid.StringMatching("[a-z]{1,12}").Draw(t, "name")
		combined := AgentNames([]string{name}, []Worker{{Name: name}})
		if len(combined) != 1 || combined[0] != name {
			t.Fatalf("duplicate agent %v", combined)
		}
		if a, _ := SocketName("/state/" + name); len(a) != 9 {
			t.Fatalf("invalid socket %q", a)
		}
		worker := Worker{
			ID: "id", GroupID: "build", Name: name + "/bad", Harness: "codex", Model: "gpt-6-sol", Effort: "high", Issue: 28,
			Kind: "feat", Slug: "registry", Branch: "feat/28-registry", WorktreePath: "/repo/.worktrees/feat-28-registry", BriefPath: "/brief", CreatedAt: "now",
		}
		if err := ValidateWorker(worker); err == nil {
			t.Fatalf("accepted invalid worker name %q", worker.Name)
		}
	})
}
