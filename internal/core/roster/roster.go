// Package roster validates worker records and computes lifecycle and worktree values.
package roster

import (
	"crypto/sha256"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

// SocketName gives each state directory a short private tmux socket name.
func SocketName(stateDir string) (string, error) {
	if !filepath.IsAbs(stateDir) {
		return "", fmt.Errorf("state directory must be absolute")
	}
	sum := sha256.Sum256([]byte(filepath.Clean(stateDir)))
	return fmt.Sprintf("a%x", sum[:4]), nil
}

// AgentNames combines initial identities and recorded workers once each.
func AgentNames(initial []string, workers []Worker) []string {
	names := make([]string, 0, len(initial)+len(workers))
	seen := make(map[string]bool, len(initial)+len(workers))
	for _, name := range initial {
		if !seen[name] {
			names = append(names, name)
			seen[name] = true
		}
	}
	for _, worker := range workers {
		if !seen[worker.Name] {
			names = append(names, worker.Name)
			seen[worker.Name] = true
		}
	}
	return names
}

// State is a worker or group lifecycle state.
type State string

const (
	Requested State = "requested"
	Starting  State = "starting"
	Running   State = "running"
	Stopping  State = "stopping"
	Stopped   State = "stopped"
	Failed    State = "failed"
)

// Group is one tmux-backed roster namespace.
type Group struct {
	ID, Name, RepoPath, TmuxSession, TmuxGeneration, CreatedAt string
	State                                                      State
}

// PrepareStop permits a shutdown retry and leaves an already stopped record alone.
func PrepareStop(state State) (State, error) {
	switch state {
	case Running, Stopping, Failed:
		return Stopping, nil
	case Stopped:
		return Stopped, nil
	default:
		return "", fmt.Errorf("cannot stop state %q", state)
	}
}

// CompleteStop accepts a completed or repeated shutdown.
func CompleteStop(state State) (State, error) {
	if state == Stopped {
		return Stopped, nil
	}
	return Transition(state, Stopped)
}

// ShouldStopWorker selects workers that may still own a live window.
func ShouldStopWorker(state State) bool {
	return state == Running || state == Stopping || state == Failed
}

// CanNudge requires a running record and a recorded window.
func CanNudge(w Worker) bool { return w.State == Running && w.WindowID != "" }

// CanCapture requires a running record and a recorded window.
func CanCapture(w Worker) bool { return w.State == Running && w.WindowID != "" }

// OwnsGroup compares the durable group generation with the live marker.
func OwnsGroup(generation, liveGeneration string) bool {
	return generation != "" && generation == liveGeneration
}

// OwnsWindow compares persisted identity to a live tmux observation.
func OwnsWindow(generation, liveGeneration, workerID, liveWorkerID string) bool {
	return OwnsGroup(generation, liveGeneration) && workerID != "" && workerID == liveWorkerID
}

// Worker is a durable record of one harness window and worktree.
type Worker struct {
	ID, GroupID, Name, Harness, Model, Effort                   string
	Issue                                                       int
	Kind, Slug, Branch, WorktreePath, BriefPath, CredentialPath string
	WindowID, CreatedAt, UpdatedAt                              string
	State                                                       State
}

// Branch returns the issue branch and rejects names that escape its convention.
func Branch(kind string, issue int, slug string) (string, error) {
	switch kind {
	case "feat", "fix", "docs", "exp", "chore", "research":
	default:
		return "", fmt.Errorf("invalid branch type %q", kind)
	}
	if issue < 1 || !validSlug(slug) {
		return "", fmt.Errorf("invalid issue or slug")
	}
	return kind + "/" + strconv.Itoa(issue) + "-" + slug, nil
}

// Worktree returns the repository-local worktree path for a branch.
func Worktree(repo, branch string) (string, error) {
	parts := strings.Split(branch, "/")
	if len(parts) != 2 {
		return "", fmt.Errorf("invalid branch %q", branch)
	}
	name := strings.SplitN(parts[1], "-", 2)
	if len(name) != 2 {
		return "", fmt.Errorf("invalid branch %q", branch)
	}
	issue, err := strconv.Atoi(name[0])
	if err != nil {
		return "", err
	}
	valid, err := Branch(parts[0], issue, name[1])
	if err != nil || valid != branch {
		return "", fmt.Errorf("invalid branch %q", branch)
	}
	if repo == "" || !filepath.IsAbs(repo) {
		return "", fmt.Errorf("repository path must be absolute")
	}
	return filepath.Join(repo, ".worktrees", parts[0]+"-"+parts[1]), nil
}

// Transition applies one permitted state change.
func Transition(from, to State) (State, error) {
	allowed := map[State][]State{
		Requested: {Starting, Failed},
		Starting:  {Running, Failed},
		Running:   {Stopping, Failed},
		Stopping:  {Stopped, Failed},
		Stopped:   {Starting},
		Failed:    {Starting, Stopping},
	}
	for _, next := range allowed[from] {
		if next == to {
			return to, nil
		}
	}
	return "", fmt.Errorf("invalid state transition %q to %q", from, to)
}

// ValidateWorker checks fields required before a worker enters the registry.
func ValidateWorker(w Worker) error {
	if err := layout.ValidAgent(w.Name); err != nil {
		return err
	}
	if w.ID == "" || w.GroupID == "" || w.Model == "" || w.Effort == "" || w.CreatedAt == "" {
		return fmt.Errorf("worker is missing required fields")
	}
	branch, err := Branch(w.Kind, w.Issue, w.Slug)
	if err != nil {
		return err
	}
	if w.Branch != branch || !filepath.IsAbs(w.WorktreePath) || !filepath.IsAbs(w.BriefPath) || !filepath.IsAbs(w.CredentialPath) {
		return fmt.Errorf("worker branch or paths are invalid")
	}
	switch w.Harness {
	case "claude", "codex", "agy":
	default:
		return fmt.Errorf("invalid harness %q", w.Harness)
	}
	return nil
}

func validSlug(slug string) bool {
	if slug == "" || strings.HasPrefix(slug, "-") || strings.HasSuffix(slug, "-") {
		return false
	}
	for _, r := range slug {
		if r != '-' && (r < 'a' || r > 'z') && (r < '0' || r > '9') {
			return false
		}
	}
	return true
}
