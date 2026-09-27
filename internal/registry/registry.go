// Package registry stores group and worker values in a file-backed SQLite database.
package registry

import (
	"context"
	"database/sql"
	"embed"
	"fmt"
	"os"
	"path/filepath"

	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
	_ "modernc.org/sqlite"
)

//go:embed schema.sql
var schema embed.FS

// Registry owns one database handle.
type Registry struct{ db *sql.DB }

// Open opens or migrates the registry at path.
func Open(path string) (*Registry, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	closeOnError := func(err error) (*Registry, error) { _ = db.Close(); return nil, err }
	var version int
	if err := db.QueryRow("PRAGMA user_version").Scan(&version); err != nil {
		return closeOnError(err)
	}
	if version > 2 {
		return closeOnError(fmt.Errorf("registry schema version %d is newer than supported version 2", version))
	}
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		return closeOnError(err)
	}
	switch version {
	case 0:
		migration, err := schema.ReadFile("schema.sql")
		if err != nil {
			return closeOnError(err)
		}
		if _, err := db.Exec(string(migration)); err != nil {
			return closeOnError(err)
		}
	case 1:
		if _, err := db.Exec("ALTER TABLE groups ADD COLUMN tmux_generation TEXT NOT NULL DEFAULT ''; PRAGMA user_version = 2;"); err != nil {
			return closeOnError(err)
		}
	}
	return &Registry{db: db}, nil
}

// Close releases the database handle.
func (r *Registry) Close() error { return r.db.Close() }

// CreateGroup records one host-tmux group.
func (r *Registry) CreateGroup(ctx context.Context, g roster.Group) error {
	_, err := r.db.ExecContext(ctx, `INSERT INTO groups(id,name,repo_path,tmux_session,tmux_generation,state,created_at) VALUES(?,?,?,?,?,?,?)`,
		g.ID, g.Name, g.RepoPath, g.TmuxSession, g.TmuxGeneration, g.State, g.CreatedAt)
	return err
}

// Group loads one named group.
func (r *Registry) Group(ctx context.Context, name string) (roster.Group, error) {
	var g roster.Group
	err := r.db.QueryRowContext(ctx, `SELECT id,name,repo_path,tmux_session,tmux_generation,state,created_at FROM groups WHERE name=?`, name).
		Scan(&g.ID, &g.Name, &g.RepoPath, &g.TmuxSession, &g.TmuxGeneration, &g.State, &g.CreatedAt)
	return g, err
}

// SetGroupGeneration stores the tmux generation assigned at group start.
func (r *Registry) SetGroupGeneration(ctx context.Context, id, generation string) error {
	_, err := r.db.ExecContext(ctx, `UPDATE groups SET tmux_generation=? WHERE id=?`, generation, id)
	return err
}

// SetGroupState stores a state computed by the core.
func (r *Registry) SetGroupState(ctx context.Context, id string, state roster.State) error {
	_, err := r.db.ExecContext(ctx, `UPDATE groups SET state=? WHERE id=?`, state, id)
	return err
}

// CreateWorker inserts a validated worker value.
func (r *Registry) CreateWorker(ctx context.Context, w roster.Worker) error {
	if err := roster.ValidateWorker(w); err != nil {
		return err
	}
	_, err := r.db.ExecContext(ctx, `INSERT INTO workers(id,group_id,name,harness,model,effort,issue,kind,slug,branch,worktree_path,brief_path,credential_path,window_id,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		w.ID, w.GroupID, w.Name, w.Harness, w.Model, w.Effort, w.Issue, w.Kind, w.Slug, w.Branch, w.WorktreePath, w.BriefPath, w.CredentialPath, w.WindowID, w.State, w.CreatedAt, w.UpdatedAt)
	return err
}

// Worker loads one worker by group and name.
func (r *Registry) Worker(ctx context.Context, groupID, name string) (roster.Worker, error) {
	return scanWorker(r.db.QueryRowContext(ctx, `SELECT id,group_id,name,harness,model,effort,issue,kind,slug,branch,worktree_path,brief_path,credential_path,window_id,state,created_at,updated_at FROM workers WHERE group_id=? AND name=?`, groupID, name))
}

// ListWorkers returns all workers in a group, ordered by name.
func (r *Registry) ListWorkers(ctx context.Context, groupID string) ([]roster.Worker, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT id,group_id,name,harness,model,effort,issue,kind,slug,branch,worktree_path,brief_path,credential_path,window_id,state,created_at,updated_at FROM workers WHERE group_id=? ORDER BY name`, groupID)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()
	workers := []roster.Worker{}
	for rows.Next() {
		w, err := scanWorker(rows)
		if err != nil {
			return nil, err
		}
		workers = append(workers, w)
	}
	return workers, rows.Err()
}

// UpdateWorker stores a state, window id, and timestamp computed by the caller.
func (r *Registry) UpdateWorker(ctx context.Context, w roster.Worker) error {
	_, err := r.db.ExecContext(ctx, `UPDATE workers SET state=?,window_id=?,credential_path=?,updated_at=? WHERE id=?`,
		w.State, w.WindowID, w.CredentialPath, w.UpdatedAt, w.ID)
	return err
}

type scanner interface{ Scan(dest ...any) error }

func scanWorker(row scanner) (roster.Worker, error) {
	var w roster.Worker
	err := row.Scan(&w.ID, &w.GroupID, &w.Name, &w.Harness, &w.Model, &w.Effort, &w.Issue, &w.Kind, &w.Slug,
		&w.Branch, &w.WorktreePath, &w.BriefPath, &w.CredentialPath, &w.WindowID, &w.State, &w.CreatedAt, &w.UpdatedAt)
	return w, err
}
