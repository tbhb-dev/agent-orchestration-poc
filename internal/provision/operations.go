package provision

import (
	"context"
	"fmt"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

// Capture reads the recorded worker's tmux pane.
func (s *Service) Capture(ctx context.Context, name string, lines int) (string, error) {
	w, err := s.worker(ctx, name)
	if err != nil {
		return "", err
	}
	if w.WindowID == "" {
		return "", fmt.Errorf("worker %s has no tmux window", name)
	}
	return s.Tmux.Capture(ctx, w.WindowID, lines)
}

// Nudge sends only the fixed inbox pointer through bracketed paste.
func (s *Service) Nudge(ctx context.Context, name string) error {
	w, err := s.worker(ctx, name)
	if err != nil {
		return err
	}
	if w.State != roster.Running || w.WindowID == "" {
		return fmt.Errorf("worker %s is not running", name)
	}
	return s.Tmux.Nudge(ctx, w.WindowID, fmt.Sprintf("agentd-%d", time.Now().UnixNano()))
}

// Stop kills only a recorded worker window and retains its worktree.
func (s *Service) Stop(ctx context.Context, name string) (roster.Worker, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stop(ctx, name)
}

func (s *Service) stop(ctx context.Context, name string) (roster.Worker, error) {
	w, err := s.worker(ctx, name)
	if err != nil {
		return w, err
	}
	w.State, err = roster.Transition(w.State, roster.Stopping)
	if err != nil {
		return w, err
	}
	w.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	if err := s.Registry.UpdateWorker(ctx, w); err != nil {
		return w, err
	}
	if w.WindowID != "" {
		if err := s.Tmux.StopWorker(ctx, w.WindowID); err != nil {
			w.State = roster.Failed
			_ = s.Registry.UpdateWorker(ctx, w)
			return w, err
		}
	}
	w.State, err = roster.Transition(w.State, roster.Stopped)
	if err != nil {
		return w, err
	}
	w.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	return w, s.Registry.UpdateWorker(ctx, w)
}

// GroupStop stops workers and the private group session.
func (s *Service) GroupStop(ctx context.Context) (roster.Group, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return g, err
	}
	g.State, err = roster.Transition(g.State, roster.Stopping)
	if err != nil {
		return g, err
	}
	if err := s.Registry.SetGroupState(ctx, g.ID, g.State); err != nil {
		return g, err
	}
	workers, err := s.Registry.ListWorkers(ctx, g.ID)
	if err != nil {
		return g, err
	}
	for _, w := range workers {
		if w.State == roster.Running {
			if _, err := s.stop(ctx, w.Name); err != nil {
				return g, err
			}
		}
	}
	if err := s.Tmux.StopGroup(ctx, g.TmuxSession); err != nil {
		return g, err
	}
	g.State, err = roster.Transition(g.State, roster.Stopped)
	if err != nil {
		return g, err
	}
	return g, s.Registry.SetGroupState(ctx, g.ID, g.State)
}

func (s *Service) worker(ctx context.Context, name string) (roster.Worker, error) {
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return roster.Worker{}, err
	}
	return s.Registry.Worker(ctx, g.ID, name)
}
