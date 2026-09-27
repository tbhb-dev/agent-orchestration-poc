//go:build integration

package tmux

import (
	"context"
	"crypto/rand"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
)

func TestPrivateServerStandIn(t *testing.T) {
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux is not installed")
	}
	var socketID [4]byte
	if _, err := rand.Read(socketID[:]); err != nil {
		t.Fatal(err)
	}
	b := Backend{Socket: fmt.Sprintf("t%x", socketID)}
	ctx := t.Context()
	if present, err := b.GroupPresent(ctx, "build"); err != nil || present {
		t.Fatalf("missing group = %t, %v", present, err)
	}
	if err := b.StartGroup(ctx, "build"); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _, _ = b.run(context.Background(), "kill-server") })
	if err := b.SetGroupGeneration(ctx, "build", "generation"); err != nil {
		t.Fatal(err)
	}
	if got, err := b.GroupGeneration(ctx, "build"); err != nil || got != "generation" {
		t.Fatalf("generation = %q, %v", got, err)
	}
	brief := filepath.Join(t.TempDir(), "brief's file.md")
	if err := os.WriteFile(brief, []byte("STANDIN BRIEF\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	recipe := launch.Recipe{Args: []string{"sh", "-c", `cat "$1"; printf 'GROUP:%s\n' "$AGENTCTL_GROUP"; IFS= read -r line; printf 'INPUT:%s\n' "$line"; sleep 3`, "sh", brief}, Env: map[string]string{"AGENTCTL_GROUP": "build"}}
	id, err := b.StartWorker(ctx, "build", "standin", filepath.Dir(brief), recipe)
	if err != nil {
		t.Fatal(err)
	}
	if err := b.SetWindowOwner(ctx, id, "build/standin"); err != nil {
		t.Fatal(err)
	}
	if got, present, err := b.WindowOwner(ctx, "build", id); err != nil || !present || got != "build/standin" {
		t.Fatalf("window owner = %q, %t, %v", got, present, err)
	}
	var capture string
	for range 100 {
		capture, err = b.Capture(ctx, id, 20)
		if err == nil && strings.Contains(capture, "STANDIN BRIEF") && strings.Contains(capture, "GROUP:build") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	if !strings.Contains(capture, "STANDIN BRIEF") || !strings.Contains(capture, "GROUP:build") {
		t.Fatalf("stand-in did not print brief: %q, %v", capture, err)
	}
	if err := b.Nudge(ctx, id, "standin-pointer"); err != nil {
		t.Fatal(err)
	}
	for range 100 {
		capture, err = b.Capture(ctx, id, 20)
		if err == nil && strings.Contains(capture, "Check agentctl for pending messages.") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	if !strings.Contains(capture, "Check agentctl for pending messages.") {
		t.Fatalf("nudge did not reach stand-in: %q, %v", capture, err)
	}
	t.Logf("stand-in capture: %s", capture)
	if err := b.StopWorker(ctx, id); err != nil {
		t.Fatal(err)
	}
	if err := b.StopGroup(ctx, "build"); err != nil {
		t.Fatal(err)
	}
}

func TestGroupPresenceReportsUnexpectedError(t *testing.T) {
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux is not installed")
	}
	b := Backend{Socket: strings.Repeat("x", 120)}
	if present, err := b.GroupPresent(t.Context(), "build"); err == nil || present {
		t.Fatalf("invalid socket = %t, %v", present, err)
	}
}
