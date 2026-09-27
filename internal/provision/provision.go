// Package provision connects registry values to git, the bus, and host tmux.
package provision

import (
	"context"
	"crypto/rand"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/backend/tmux"
	"github.com/tbhb/agent-orchestration-poc/internal/bus"
	"github.com/tbhb/agent-orchestration-poc/internal/core/launch"
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
	"github.com/tbhb/agent-orchestration-poc/internal/registry"
)

// SpawnRequest supplies one issue assignment and the source brief file.
type SpawnRequest struct {
	Name, Harness, Model, Effort, Kind, Slug, BriefPath string
	Issue                                               int
}

// Status joins durable group state with current tmux availability.
type Status struct {
	Group       roster.Group
	TmuxSocket  string
	TmuxRunning bool
	Workers     []roster.Worker
}

// Service owns the shell resources for a build group.
type Service struct {
	mu                         sync.Mutex
	Registry                   *registry.Registry
	Bus                        *bus.Bus
	Tmux                       tmux.Backend
	StateDir, RepoPath, GitDir string
	Port                       int
	InitialAgents              []string
}

// Open starts the bus from the registry's durable worker roster.
func Open(ctx context.Context, stateDir, gitDir string, port int, initialAgents []string) (*Service, error) {
	if !filepath.IsAbs(stateDir) || !filepath.IsAbs(gitDir) || port < 1 || port > 65535 {
		return nil, fmt.Errorf("absolute state and git directories and valid port are required")
	}
	r, err := registry.Open(filepath.Join(stateDir, "registry.sqlite"))
	if err != nil {
		return nil, err
	}
	group, err := r.Group(ctx, "build")
	if errors.Is(err, sql.ErrNoRows) {
		group = roster.Group{ID: "build", Name: "build", RepoPath: filepath.Dir(gitDir), TmuxSession: "build", State: roster.Stopped, CreatedAt: time.Now().UTC().Format(time.RFC3339Nano)}
		err = r.CreateGroup(ctx, group)
	}
	if err != nil {
		_ = r.Close()
		return nil, err
	}
	workers, err := r.ListWorkers(ctx, group.ID)
	if err != nil {
		_ = r.Close()
		return nil, err
	}
	agents := roster.AgentNames(initialAgents, workers)
	broker, err := bus.Start(ctx, bus.Config{StateDir: filepath.Join(stateDir, "bus"), Port: port, Groups: []bus.Group{{Name: "build", Agents: agents}}})
	if err != nil {
		_ = r.Close()
		return nil, err
	}
	socket, err := roster.SocketName(stateDir)
	if err != nil {
		broker.Close()
		_ = r.Close()
		return nil, err
	}
	return &Service{Registry: r, Bus: broker, Tmux: tmux.Backend{Socket: socket}, StateDir: stateDir, RepoPath: group.RepoPath, GitDir: gitDir, Port: port, InitialAgents: initialAgents}, nil
}

// Close releases the bus and registry.
func (s *Service) Close() error {
	s.Bus.Close()
	return s.Registry.Close()
}

// GroupStart starts the group's private tmux session.
func (s *Service) GroupStart(ctx context.Context) (roster.Group, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.groupStart(ctx)
}

func (s *Service) groupStart(ctx context.Context) (roster.Group, error) {
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return g, err
	}
	exists, err := s.Tmux.GroupPresent(ctx, g.TmuxSession)
	if err != nil {
		return g, err
	}
	if exists {
		live, err := s.Tmux.GroupGeneration(ctx, g.TmuxSession)
		if err != nil {
			return g, err
		}
		if !roster.OwnsGroup(g.TmuxGeneration, live) {
			return g, fmt.Errorf("tmux group %s has a different generation", g.Name)
		}
		return g, nil
	}
	if _, err := roster.Transition(g.State, roster.Starting); err != nil {
		return g, err
	}
	if err := s.Registry.SetGroupState(ctx, g.ID, roster.Starting); err != nil {
		return g, err
	}
	if err := s.Tmux.StartGroup(ctx, g.TmuxSession); err != nil {
		_ = s.Registry.SetGroupState(ctx, g.ID, roster.Failed)
		return g, err
	}
	var generation [16]byte
	if _, err := rand.Read(generation[:]); err != nil {
		return g, err
	}
	g.TmuxGeneration = fmt.Sprintf("%x", generation)
	if err := s.Tmux.SetGroupGeneration(ctx, g.TmuxSession, g.TmuxGeneration); err != nil {
		return g, err
	}
	if err := s.Registry.SetGroupGeneration(ctx, g.ID, g.TmuxGeneration); err != nil {
		return g, err
	}
	g.State = roster.Running
	return g, s.Registry.SetGroupState(ctx, g.ID, g.State)
}

// GroupStatus reports registry state and the private tmux server state.
func (s *Service) GroupStatus(ctx context.Context) (Status, error) {
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return Status{}, err
	}
	workers, err := s.Registry.ListWorkers(ctx, g.ID)
	if err != nil {
		return Status{}, err
	}
	return Status{Group: g, TmuxSocket: s.Tmux.Socket, TmuxRunning: s.Tmux.GroupExists(ctx, g.TmuxSession), Workers: workers}, nil
}

// List returns the durable worker roster.
func (s *Service) List(ctx context.Context) ([]roster.Worker, error) {
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return nil, err
	}
	return s.Registry.ListWorkers(ctx, g.ID)
}

// Spawn creates a worktree, registers credentials, and launches one harness window.
func (s *Service) Spawn(ctx context.Context, req SpawnRequest) (w roster.Worker, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := layout.ValidAgent(req.Name); err != nil {
		return w, err
	}
	branch, err := roster.Branch(req.Kind, req.Issue, req.Slug)
	if err != nil {
		return w, err
	}
	worktree, err := roster.Worktree(s.RepoPath, branch)
	if err != nil {
		return w, err
	}
	brief, err := os.ReadFile(req.BriefPath)
	if err != nil {
		return w, err
	}
	g, err := s.Registry.Group(ctx, "build")
	if err != nil {
		return w, err
	}
	credPath, err := s.Bus.CredentialPath(g.Name, req.Name)
	if err != nil {
		return w, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	w = roster.Worker{
		ID: g.Name + "/" + req.Name, GroupID: g.ID, Name: req.Name, Harness: req.Harness, Model: req.Model, Effort: req.Effort,
		Issue: req.Issue, Kind: req.Kind, Slug: req.Slug, Branch: branch, WorktreePath: worktree,
		BriefPath: filepath.Join(s.StateDir, "briefs", req.Name+".md"), CredentialPath: credPath,
		State: roster.Requested, CreatedAt: now, UpdatedAt: now,
	}
	settingsPath := filepath.Join(s.StateDir, "settings", w.Name+".json")
	recipe, err := launch.Build(launch.Spec{
		Harness: w.Harness, Model: w.Model, Effort: w.Effort, WorktreePath: w.WorktreePath, BriefPath: w.BriefPath,
		CredentialPath: w.CredentialPath, SettingsPath: settingsPath, Group: g.Name, Name: w.Name, BusURL: s.Bus.URL(), WritableRoots: []string{s.GitDir},
	})
	if err != nil {
		return w, err
	}
	g, err = s.groupStart(ctx)
	if err != nil {
		return w, err
	}
	if err := s.Registry.CreateWorker(ctx, w); err != nil {
		return w, err
	}
	defer func() {
		if err != nil {
			w.State = roster.Failed
			w.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
			_ = s.Registry.UpdateWorker(ctx, w)
		}
	}()
	w, err = s.startWorker(ctx, g, w, brief, recipe)
	return w, err
}

func (s *Service) startWorker(ctx context.Context, g roster.Group, w roster.Worker, brief []byte, recipe launch.Recipe) (roster.Worker, error) {
	var err error
	w.State, err = roster.Transition(w.State, roster.Starting)
	if err != nil {
		return w, err
	}
	if err = s.Registry.UpdateWorker(ctx, w); err != nil {
		return w, err
	}
	if err = gitWorktree(ctx, s.RepoPath, w.Branch, w.WorktreePath); err != nil {
		return w, err
	}
	if err = os.MkdirAll(filepath.Dir(w.BriefPath), 0o700); err != nil {
		return w, err
	}
	if err = os.WriteFile(w.BriefPath, brief, 0o600); err != nil {
		return w, err
	}
	if err = s.registerAgent(ctx, g, w.Name); err != nil {
		return w, err
	}
	settingsPath := filepath.Join(s.StateDir, "settings", w.Name+".json")
	if settings := launch.Settings(w.Harness); len(settings) != 0 {
		if err = writeSettings(settingsPath, settings); err != nil {
			return w, err
		}
	}
	w.WindowID, err = s.Tmux.StartWorker(ctx, g.TmuxSession, w.Name, w.WorktreePath, recipe)
	if err != nil {
		return w, err
	}
	if err = s.Tmux.SetWindowOwner(ctx, w.WindowID, w.ID); err != nil {
		return w, err
	}
	w.State, err = roster.Transition(w.State, roster.Running)
	if err != nil {
		return w, err
	}
	w.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	return w, s.Registry.UpdateWorker(ctx, w)
}

func (s *Service) registerAgent(ctx context.Context, g roster.Group, name string) error {
	workers, err := s.Registry.ListWorkers(ctx, g.ID)
	if err != nil {
		return err
	}
	agents := roster.AgentNames(s.InitialAgents, workers)
	return s.Bus.RegisterAgent(ctx, bus.Config{
		StateDir: filepath.Join(s.StateDir, "bus"), Port: s.Port,
		Groups: []bus.Group{{Name: g.Name, Agents: agents}},
	}, g.Name, name)
}

func gitWorktree(ctx context.Context, repo, branch, path string) error {
	command := exec.CommandContext(ctx, "git", "-C", repo, "worktree", "add", "-b", branch, path)
	output, err := command.CombinedOutput()
	if err != nil {
		return fmt.Errorf("git worktree add: %w: %s", err, output)
	}
	return nil
}

func writeSettings(path string, content []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	return os.WriteFile(path, content, 0o600)
}
