package provision

import (
	"context"
	"fmt"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

// Capture reads the recorded worker's tmux pane.
func (s *Service) Capture(ctx context.Context, name string, lines int) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	w, err := s.worker(ctx, name)
	if err != nil {
		return "", err
	}
	if !roster.CanCapture(w) {
		return "", fmt.Errorf("worker %s is not running", name)
	}
	present, err := s.windowPresent(ctx, w)
	if err != nil {
		return "", err
	}
	if !present {
		return "", fmt.Errorf("worker %s has no live tmux window", name)
	}
	return s.Tmux.Capture(ctx, w.WindowID, lines)
}

// Nudge sends only the fixed inbox pointer through bracketed paste.
func (s *Service) Nudge(ctx context.Context, name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	w, err := s.worker(ctx, name)
	if err != nil {
		return err
	}
	if !roster.CanNudge(w) {
		return fmt.Errorf("worker %s is not running", name)
	}
	present, err := s.windowPresent(ctx, w)
	if err != nil {
		return err
	}
	if !present {
		return fmt.Errorf("worker %s has no live tmux window", name)
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
	next, err := roster.PrepareStop(w.State)
	if err != nil {
		return w, err
	}
	if next == roster.Stopped {
		return w, nil
	}
	present, err := s.windowPresent(ctx, w)
	if err != nil {
		return w, err
	}
	w.State = next
	w.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	if err := s.Registry.UpdateWorker(ctx, w); err != nil {
		return w, err
	}
	if present {
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
	g.State, err = roster.PrepareStop(g.State)
	if err != nil {
		return g, err
	}
	exists, err := s.groupPresentOwned(ctx, g)
	if err != nil {
		return g, err
	}
	if g.State == roster.Stopped && !exists {
		return g, nil
	}
	if err := s.Registry.SetGroupState(ctx, g.ID, g.State); err != nil {
		return g, err
	}
	if err := s.stopRecordedWorkers(ctx, g); err != nil {
		return g, err
	}
	exists, err = s.groupPresentOwned(ctx, g)
	if err != nil {
		return g, err
	}
	if exists {
		if err := s.Tmux.StopGroup(ctx, g.TmuxSession); err != nil {
			return g, err
		}
	}
	g.State, err = roster.CompleteStop(g.State)
	if err != nil {
		return g, err
	}
	return g, s.Registry.SetGroupState(ctx, g.ID, g.State)
}

func (s *Service) groupPresentOwned(ctx context.Context, g roster.Group) (bool, error) {
	exists, err := s.Tmux.GroupPresent(ctx, g.TmuxSession)
	if err != nil || !exists {
		return exists, err
	}
	return true, s.groupOwned(ctx, g)
}

func (s *Service) groupOwned(ctx context.Context, g roster.Group) error {
	live, err := s.Tmux.GroupGeneration(ctx, g.TmuxSession)
	if err != nil {
		return err
	}
	if !roster.OwnsGroup(g.TmuxGeneration, live) {
		return fmt.Errorf("tmux group %s has a different generation", g.Name)
	}
	return nil
}

func (s *Service) stopRecordedWorkers(ctx context.Context, g roster.Group) error {
	workers, err := s.Registry.ListWorkers(ctx, g.ID)
	if err != nil {
		return err
	}
	for _, w := range workers {
		if roster.ShouldStopWorker(w.State) {
			if _, err := s.stop(ctx, w.Name); err != nil {
				return err
			}
		}
	}
	return nil
}

func (s *Service) windowPresent(ctx context.Context, w roster.Worker) (bool, error) {
	if w.WindowID == "" {
		return false, nil
	}
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return false, err
	}
	exists, err := s.groupPresentOwned(ctx, g)
	if err != nil {
		return false, err
	}
	if !exists {
		return false, nil
	}
	live, err := s.Tmux.GroupGeneration(ctx, g.TmuxSession)
	if err != nil {
		return false, err
	}
	owner, present, err := s.Tmux.WindowOwner(ctx, g.TmuxSession, w.WindowID)
	if err != nil || !present {
		return present, err
	}
	if !roster.OwnsWindow(g.TmuxGeneration, live, w.ID, owner) {
		return false, fmt.Errorf("tmux window %s belongs to a different worker", w.WindowID)
	}
	return true, nil
}

func (s *Service) worker(ctx context.Context, name string) (roster.Worker, error) {
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return roster.Worker{}, err
	}
	return s.Registry.Worker(ctx, g.ID, name)
}
