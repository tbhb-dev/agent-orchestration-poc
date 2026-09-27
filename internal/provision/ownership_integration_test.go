//go:build integration

package provision

import (
	"context"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

func privateService(t *testing.T) (*Service, string) {
	t.Helper()
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux is not installed")
	}
	state, err := os.MkdirTemp("", "agentd28-review-")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.RemoveAll(state) })
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	_ = listener.Close()
	s, err := Open(t.Context(), state, filepath.Join(state, "repo", ".git"), port, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_ = s.Tmux.StopGroup(context.Background(), "build")
		_ = s.Close()
	})
	if _, err := s.GroupStart(t.Context()); err != nil {
		t.Fatal(err)
	}
	return s, state
}

func recordedStandin(t *testing.T, s *Service, state, name string) roster.Worker {
	t.Helper()
	id, err := s.Tmux.StartWorker(t.Context(), "build", name, state, launch.Recipe{Args: []string{"sh", "-c", "sleep 30"}})
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Tmux.SetWindowOwner(t.Context(), id, "build/"+name); err != nil {
		t.Fatal(err)
	}
	w := roster.Worker{
		ID: "build/" + name, GroupID: "build", Name: name, Harness: "codex", Model: "standin", Effort: "high", Issue: 28,
		Kind: "feat", Slug: name, Branch: "feat/28-" + name, WorktreePath: filepath.Join(state, "work", name),
		BriefPath: filepath.Join(state, "brief"), CredentialPath: filepath.Join(state, "seed"), WindowID: id,
		State: roster.Running, CreatedAt: "2026-09-26T00:00:00Z", UpdatedAt: "2026-09-26T00:00:00Z",
	}
	if err := s.Registry.CreateWorker(t.Context(), w); err != nil {
		t.Fatal(err)
	}
	return w
}

func TestRejectReusedWindowID(t *testing.T) {
	s, state := privateService(t)
	old := recordedStandin(t, s, state, "old")
	if err := s.Tmux.StopGroup(t.Context(), "build"); err != nil {
		t.Fatal(err)
	}
	if err := s.Tmux.StartGroup(t.Context(), "build"); err != nil {
		t.Fatal(err)
	}
	replacement, err := s.Tmux.StartWorker(t.Context(), "build", "replacement", state, launch.Recipe{Args: []string{"sh", "-c", "sleep 30"}})
	if err != nil || replacement != old.WindowID {
		t.Fatalf("replacement window = %q, %v; old = %q", replacement, err, old.WindowID)
	}
	if _, err := s.Capture(t.Context(), old.Name, 5); err == nil {
		t.Fatal("captured replacement through stale record")
	}
	if err := s.Nudge(t.Context(), old.Name); err == nil {
		t.Fatal("nudged replacement through stale record")
	}
	if _, err := s.Stop(t.Context(), old.Name); err == nil {
		t.Fatal("stopped replacement through stale record")
	}
	if _, err := s.Tmux.Capture(t.Context(), replacement, 5); err != nil {
		t.Fatalf("replacement window was killed: %v", err)
	}
}

func TestGroupStopAfterWindowExitAndRetry(t *testing.T) {
	s, state := privateService(t)
	exited := recordedStandin(t, s, state, "exited")
	_ = recordedStandin(t, s, state, "remaining")
	if err := s.Tmux.StopWorker(t.Context(), exited.WindowID); err != nil {
		t.Fatal(err)
	}
	if _, err := s.GroupStop(t.Context()); err != nil {
		t.Fatalf("first group stop: %v", err)
	}
	if _, err := s.GroupStop(t.Context()); err != nil {
		t.Fatalf("retry group stop: %v", err)
	}
	if s.Tmux.GroupExists(t.Context(), "build") {
		t.Fatal("group session survived shutdown")
	}
	w, err := s.Registry.Worker(t.Context(), "build", "exited")
	if err != nil || w.State != roster.Stopped {
		t.Fatalf("exited worker state = %q, %v", w.State, err)
	}
}
