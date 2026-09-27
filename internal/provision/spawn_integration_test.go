//go:build integration

package provision

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

func TestStartWorkerWritesBriefSettingsAndRegistry(t *testing.T) {
	s, state := privateService(t)
	repo := filepath.Join(state, "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{
		{"init", "-b", "main", repo},
		{"-C", repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "seed"},
	} {
		output, err := exec.CommandContext(t.Context(), "git", args...).CombinedOutput()
		if err != nil {
			t.Fatalf("git %v: %v: %s", args, err, output)
		}
	}
	group, err := s.Registry.Group(t.Context(), "build")
	if err != nil {
		t.Fatal(err)
	}
	w := roster.Worker{
		ID: "build/standin", GroupID: "build", Name: "standin", Harness: "claude", Model: "standin", Effort: "high",
		Issue: 28, Kind: "feat", Slug: "standin", Branch: "feat/28-standin",
		WorktreePath:   filepath.Join(repo, ".worktrees", "feat-28-standin"),
		BriefPath:      filepath.Join(state, "briefs", "standin.md"),
		CredentialPath: filepath.Join(state, "bus", "build", "standin.creds"),
		State:          roster.Requested, CreatedAt: "2026-09-26T00:00:00Z", UpdatedAt: "2026-09-26T00:00:00Z",
	}
	if err := s.Registry.CreateWorker(t.Context(), w); err != nil {
		t.Fatal(err)
	}
	brief := []byte("STANDIN BRIEF\n")
	w, err = s.startWorker(t.Context(), group, w, brief, launch.Recipe{Args: []string{"sh", "-c", "sleep 30"}})
	if err != nil || w.State != roster.Running || w.WindowID == "" {
		t.Fatalf("startWorker = %+v, %v", w, err)
	}
	if got, err := os.ReadFile(w.BriefPath); err != nil || !bytes.Equal(got, brief) {
		t.Fatalf("brief = %q, %v", got, err)
	}
	settings, err := os.ReadFile(filepath.Join(state, "settings", "standin.json"))
	if err != nil || !bytes.Equal(settings, launch.Settings("claude")) {
		t.Fatalf("settings = %q, %v", settings, err)
	}
	if _, err := os.Stat(w.WorktreePath); err != nil {
		t.Fatalf("worktree: %v", err)
	}
	recorded, err := s.Registry.Worker(t.Context(), "build", "standin")
	if err != nil || recorded.State != roster.Running || recorded.WindowID != w.WindowID {
		t.Fatalf("registry worker = %+v, %v", recorded, err)
	}
	if _, err := s.Stop(t.Context(), "standin"); err != nil {
		t.Fatal(err)
	}
}

func TestSpawnRejectsInvalidInputsBeforeLaunch(t *testing.T) {
	s, _ := privateService(t)
	for _, tc := range []struct {
		name string
		req  SpawnRequest
	}{
		{"invalid name", SpawnRequest{Name: "operator"}},
		{"invalid branch", SpawnRequest{Name: "worker", Kind: "feat", Issue: 0, Slug: "test"}},
		{"missing brief", SpawnRequest{Name: "worker", Kind: "feat", Issue: 28, Slug: "test", BriefPath: "/absent/brief"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := s.Spawn(t.Context(), tc.req); err == nil {
				t.Fatal("accepted invalid spawn")
			}
		})
	}
}
