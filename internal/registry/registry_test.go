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

func TestMigrateV1Group(t *testing.T) {
	path := filepath.Join(t.TempDir(), "registry.sqlite")
	db, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	_, err = db.Exec(`CREATE TABLE groups (id TEXT PRIMARY KEY, name TEXT, repo_path TEXT, tmux_session TEXT, state TEXT, created_at TEXT);
		INSERT INTO groups VALUES ('build','build','/repo','build','stopped','now'); PRAGMA user_version = 1;`)
	if err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	r, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = r.Close() }()
	group, err := r.Group(t.Context(), "build")
	if err != nil || group.TmuxGeneration != "" {
		t.Fatalf("migrated group = %+v, %v", group, err)
	}
	if err := r.SetGroupGeneration(t.Context(), group.ID, "new"); err != nil {
		t.Fatal(err)
	}
	group, err = r.Group(t.Context(), "build")
	if err != nil || group.TmuxGeneration != "new" {
		t.Fatalf("updated group = %+v, %v", group, err)
	}
}
