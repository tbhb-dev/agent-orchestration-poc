// Package tmux runs only scoped host-tmux commands for provisioned workers.
package tmux

import (
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
)

// Backend addresses one dedicated tmux server socket.
type Backend struct{ Socket string }

func (b Backend) run(ctx context.Context, args ...string) (string, error) {
	command := exec.CommandContext(ctx, "tmux", append([]string{"-L", b.Socket}, args...)...)
	output, err := command.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("tmux %s: %w: %s", args[0], err, strings.TrimSpace(string(output)))
	}
	return strings.TrimSpace(string(output)), nil
}

// StartGroup creates a dedicated session and its idle bootstrap window.
func (b Backend) StartGroup(ctx context.Context, name string) error {
	_, err := b.run(ctx, "new-session", "-d", "-s", name, "-n", "bootstrap")
	return err
}

// GroupExists checks only this backend's private server.
func (b Backend) GroupExists(ctx context.Context, name string) bool {
	_, err := b.run(ctx, "has-session", "-t", "="+name)
	return err == nil
}

// StartWorker creates one window and returns its tmux window id.
func (b Backend) StartWorker(ctx context.Context, group, name, cwd string, recipe launch.Recipe) (string, error) {
	args := []string{"new-window", "-d", "-P", "-F", "#{window_id}", "-t", "=" + group, "-n", name, "-c", cwd}
	for key, value := range recipe.Env {
		args = append(args, "-e", key+"="+value)
	}
	args = append(args, launch.ShellCommand(recipe.Args))
	return b.run(ctx, args...)
}

// Capture reads a worker's pane without attaching to it.
func (b Backend) Capture(ctx context.Context, windowID string, lines int) (string, error) {
	if lines < 1 || lines > 2000 {
		return "", fmt.Errorf("lines must be between 1 and 2000")
	}
	return b.run(ctx, "capture-pane", "-p", "-t", windowID, "-S", fmt.Sprintf("-%d", lines))
}

// Nudge pastes a fixed short pointer with bracketed paste, then sends Enter separately.
func (b Backend) Nudge(ctx context.Context, windowID, bufferID string) error {
	if _, err := b.run(ctx, "set-buffer", "-b", bufferID, "Check agentctl for pending messages."); err != nil {
		return err
	}
	if _, err := b.run(ctx, "paste-buffer", "-p", "-d", "-b", bufferID, "-t", windowID); err != nil {
		return err
	}
	_, err := b.run(ctx, "send-keys", "-t", windowID, "Enter")
	return err
}

// StopWorker kills only the recorded window id.
func (b Backend) StopWorker(ctx context.Context, windowID string) error {
	_, err := b.run(ctx, "kill-window", "-t", windowID)
	return err
}

// StopGroup kills one named session on this private server.
func (b Backend) StopGroup(ctx context.Context, name string) error {
	_, err := b.run(ctx, "kill-session", "-t", "="+name)
	return err
}
