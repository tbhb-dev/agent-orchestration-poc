//go:build integration

package provision

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

func TestGroupOperationsOnPrivateServer(t *testing.T) {
	service, state := privateService(t)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	serverDone := make(chan error, 1)
	go func() { serverDone <- service.ServeLocal(ctx) }()
	for range 20 {
		if _, err := os.Stat(filepath.Join(state, "agentd.sock")); err == nil {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	started, err := Call(t.Context(), state, Request{Operation: "group-start"})
	if err != nil || started.Status.Group.State != "running" {
		t.Fatalf("group start = %+v, %v", started, err)
	}
	status, err := Call(t.Context(), state, Request{Operation: "group-status"})
	if err != nil || !status.Status.TmuxRunning || status.Status.TmuxSocket != service.Tmux.Socket {
		t.Fatalf("group status = %+v, %v", status, err)
	}
	brief := filepath.Join(state, "standin-brief.md")
	if err := os.WriteFile(brief, []byte("STANDIN SERVICE BRIEF\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	recipe := launch.Recipe{Args: []string{"sh", "-c", `cat "$1"; IFS= read -r line; printf 'INPUT:%s\n' "$line"; sleep 3`, "sh", brief}}
	windowID, err := service.Tmux.StartWorker(t.Context(), "build", "standin", state, recipe)
	if err != nil {
		t.Fatal(err)
	}
	if err := service.Tmux.SetWindowOwner(t.Context(), windowID, "build/standin"); err != nil {
		t.Fatal(err)
	}
	w := roster.Worker{
		ID: "build/standin", GroupID: "build", Name: "standin", Harness: "codex", Model: "standin", Effort: "high", Issue: 28,
		Kind: "feat", Slug: "standin", Branch: "feat/28-standin", WorktreePath: filepath.Join(state, ".worktrees", "feat-28-standin"),
		BriefPath: brief, CredentialPath: filepath.Join(state, "seed"), WindowID: windowID, State: roster.Running, CreatedAt: "2026-09-26T00:00:00Z", UpdatedAt: "2026-09-26T00:00:00Z",
	}
	if err := service.Registry.CreateWorker(t.Context(), w); err != nil {
		t.Fatal(err)
	}
	listed, err := Call(t.Context(), state, Request{Operation: "list"})
	if err != nil || len(listed.Workers) != 1 {
		t.Fatalf("list = %+v, %v", listed, err)
	}
	var captured Response
	for range 20 {
		captured, err = Call(t.Context(), state, Request{Operation: "capture", Name: "standin", Lines: 20})
		if err == nil && strings.Contains(captured.Capture, "STANDIN SERVICE BRIEF") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	if err != nil || !strings.Contains(captured.Capture, "STANDIN SERVICE BRIEF") {
		t.Fatalf("capture = %+v, %v", captured, err)
	}
	if _, err := Call(t.Context(), state, Request{Operation: "nudge", Name: "standin"}); err != nil {
		t.Fatal(err)
	}
	for range 20 {
		captured, err = Call(t.Context(), state, Request{Operation: "capture", Name: "standin", Lines: 20})
		if err == nil && strings.Contains(captured.Capture, "INPUT:Check agentctl for pending messages.") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	if err != nil || !strings.Contains(captured.Capture, "INPUT:Check agentctl for pending messages.") {
		t.Fatalf("nudge capture = %+v, %v", captured, err)
	}
	t.Logf("provisioner capture: %s", captured.Capture)
	if _, err := Call(t.Context(), state, Request{Operation: "stop", Name: "standin"}); err != nil {
		t.Fatal(err)
	}
	stopped, err := Call(t.Context(), state, Request{Operation: "group-stop"})
	if err != nil || stopped.Status.Group.State != "stopped" {
		t.Fatalf("group stop = %+v, %v", stopped, err)
	}
	cancel()
	if err := <-serverDone; err != nil {
		t.Fatal(err)
	}
}
