PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  repo_path TEXT NOT NULL,
  tmux_session TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK (state IN ('requested','starting','running','stopping','stopped','failed')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workers (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES groups(id),
  name TEXT NOT NULL,
  harness TEXT NOT NULL CHECK (harness IN ('claude','codex','agy')),
  model TEXT NOT NULL,
  effort TEXT NOT NULL,
  issue INTEGER NOT NULL,
  kind TEXT NOT NULL,
  slug TEXT NOT NULL,
  branch TEXT NOT NULL,
  worktree_path TEXT NOT NULL UNIQUE,
  brief_path TEXT NOT NULL,
  credential_path TEXT NOT NULL,
  window_id TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL CHECK (state IN ('requested','starting','running','stopping','stopped','failed')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (group_id, name)
);
PRAGMA user_version = 1;
