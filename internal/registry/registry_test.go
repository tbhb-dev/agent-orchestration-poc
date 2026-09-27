package registry

import (
	"database/sql"
	"path/filepath"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

func TestFileRegistryRoundTrip(t *testing.T) {
	path := filepath.Join(t.TempDir(), "registry.sqlite")
	r, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	ctx := t.Context()
	g := roster.Group{ID: "g1", Name: "build", RepoPath: "/repo", TmuxSession: "build", State: roster.Stopped, CreatedAt: "2026-09-26T00:00:00Z"}
	if err := r.CreateGroup(ctx, g); err != nil {
		t.Fatal(err)
	}
	w := roster.Worker{
		ID: "w1", GroupID: g.ID, Name: "codex-impl", Harness: "codex", Model: "gpt-6-sol", Effort: "high", Issue: 28,
		Kind: "feat", Slug: "registry-tmux", Branch: "feat/28-registry-tmux", WorktreePath: "/repo/.worktrees/feat-28-registry-tmux", BriefPath: "/brief", CredentialPath: "/state/seed", State: roster.Requested,
		CreatedAt: g.CreatedAt, UpdatedAt: g.CreatedAt,
	}
	if err := r.CreateWorker(ctx, w); err != nil {
		t.Fatal(err)
	}
	if err := r.Close(); err != nil {
		t.Fatal(err)
	}
	r, err = Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = r.Close() }()
	loaded, err := r.Worker(ctx, g.ID, w.Name)
	if err != nil || loaded != w {
		t.Fatalf("Worker() = %+v, %v", loaded, err)
	}
	w.State, w.WindowID, w.UpdatedAt = roster.Running, "@1", "2026-09-26T01:00:00Z"
	if err := r.UpdateWorker(ctx, w); err != nil {
		t.Fatal(err)
	}
	workers, err := r.ListWorkers(ctx, g.ID)
	if err != nil || len(workers) != 1 || workers[0] != w {
		t.Fatalf("ListWorkers() = %+v, %v", workers, err)
	}
	if err := r.CreateWorker(ctx, w); err == nil {
		t.Fatal("accepted duplicate worker")
	}
	if _, err := r.Worker(ctx, g.ID, "missing"); err != sql.ErrNoRows {
		t.Fatalf("missing worker error = %v", err)
	}
}
