// Package launch builds harness commands from plain worker specifications.
package launch

import (
	"fmt"
	"path/filepath"
	"strings"
)

// Spec contains only values resolved by the provisioner shell.
type Spec struct {
	Harness, Model, Effort, WorktreePath, BriefPath   string
	CredentialPath, SettingsPath, Group, Name, BusURL string
	WritableRoots                                     []string
}

// ShellCommand quotes argv for tmux's shell-command field without interpretation.
func ShellCommand(args []string) string {
	quoted := make([]string, len(args))
	for i, arg := range args {
		quoted[i] = "'" + strings.ReplaceAll(arg, "'", "'\\''") + "'"
	}
	return "exec " + strings.Join(quoted, " ")
}

// Recipe is the argv and environment for a harness process.
type Recipe struct {
	Args []string
	Env  map[string]string
}

// Build records the approved unattended flags and a short initial prompt.
func Build(spec Spec) (Recipe, error) {
	if err := validateSpec(spec); err != nil {
		return Recipe{}, err
	}
	prompt := "Read the brief at " + spec.BriefPath + " and follow it."
	var args []string
	switch spec.Harness {
	case "claude":
		args = []string{"mise", "exec", "--", "claude", "--permission-mode", "auto", "--settings", spec.SettingsPath, "--model", spec.Model, "--effort", spec.Effort}
	case "codex":
		args = []string{"mise", "exec", "--", "codex", "-s", "workspace-write", "-a", "never", "-c", "sandbox_workspace_write.network_access=true", "-c", "model_reasoning_effort=\"" + spec.Effort + "\"", "-c", "shell_environment_policy.inherit=\"all\"", "-m", spec.Model, "-C", spec.WorktreePath}
	case "agy":
		args = []string{"mise", "exec", "--", "agy", "--sandbox", "--dangerously-skip-permissions", "--model", spec.Model, "--effort", spec.Effort}
	}
	for _, root := range spec.WritableRoots {
		args = append(args, "--add-dir", root)
	}
	if spec.Harness == "agy" {
		args = append(args, "--prompt-interactive", prompt)
	} else {
		args = append(args, prompt)
	}
	return Recipe{Args: args, Env: map[string]string{
		"AGENTCTL_GROUP": spec.Group, "AGENTCTL_WORKER": spec.Name,
		"AGENTCTL_NATS_URL": spec.BusURL, "AGENTCTL_CREDS_FILE": spec.CredentialPath,
	}}, nil
}

func validateSpec(spec Spec) error {
	if spec.Model == "" || spec.Effort == "" || spec.Group == "" || spec.Name == "" || spec.BusURL == "" {
		return fmt.Errorf("model, effort, group, name, and bus URL are required")
	}
	if !allAbsolute(spec.WorktreePath, spec.BriefPath, spec.CredentialPath) {
		return fmt.Errorf("worktree, brief, and credential paths must be absolute")
	}
	if !allAbsolute(spec.WritableRoots...) {
		return fmt.Errorf("writable root must be absolute")
	}
	if !validEffort(spec.Harness, spec.Effort) {
		return fmt.Errorf("invalid effort %q for %s", spec.Effort, spec.Harness)
	}
	if spec.Harness == "claude" && !filepath.IsAbs(spec.SettingsPath) {
		return fmt.Errorf("claude settings path must be absolute")
	}
	if spec.Harness != "claude" && spec.Harness != "codex" && spec.Harness != "agy" {
		return fmt.Errorf("invalid harness %q", spec.Harness)
	}
	return nil
}

func allAbsolute(paths ...string) bool {
	for _, path := range paths {
		if !filepath.IsAbs(path) {
			return false
		}
	}
	return true
}

func validEffort(harness, effort string) bool {
	allowed := map[string][]string{
		"claude": {"low", "medium", "high", "xhigh", "max"},
		"codex":  {"low", "medium", "high", "xhigh", "max", "ultra"},
		"agy":    {"low", "medium", "high", "max"},
	}
	for _, value := range allowed[harness] {
		if value == effort {
			return true
		}
	}
	return false
}
