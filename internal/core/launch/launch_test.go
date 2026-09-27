package launch

import (
	"reflect"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestBuild(t *testing.T) {
	base := Spec{Model: "m", Effort: "high", WorktreePath: "/repo/.worktrees/feat-28-x", BriefPath: "/brief.md", CredentialPath: "/state/seed", SettingsPath: "/state/settings.json", Group: "build", Name: "worker", BusURL: "nats://127.0.0.1:4222", WritableRoots: []string{"/repo/.git"}}
	cases := []struct {
		harness string
		flags   []string
	}{
		{"claude", []string{"claude", "--permission-mode", "auto", "--settings", "/state/settings.json", "--add-dir", "/repo/.git"}},
		{"codex", []string{"codex", "-s", "workspace-write", "-a", "never", "-c", "sandbox_workspace_write.network_access=true", "--add-dir", "/repo/.git"}},
		{"agy", []string{"agy", "--sandbox", "--dangerously-skip-permissions", "--add-dir", "/repo/.git", "--prompt-interactive"}},
	}
	for _, tc := range cases {
		t.Run(tc.harness, func(t *testing.T) {
			base.Harness = tc.harness
			recipe, err := Build(base)
			if err != nil {
				t.Fatal(err)
			}
			joined := strings.Join(recipe.Args, " ")
			for _, flag := range tc.flags {
				if !strings.Contains(joined, flag) {
					t.Fatalf("recipe missing %q: %v", flag, recipe.Args)
				}
			}
			if recipe.Env["AGENTCTL_CREDS_FILE"] != "/state/seed" {
				t.Fatalf("credential path missing: %v", recipe.Env)
			}
		})
	}
}

func TestShellCommand(t *testing.T) {
	if got := ShellCommand([]string{"one", "it's", "$(false)"}); got != "exec 'one' 'it'\\''s' '$(false)'" {
		t.Fatalf("ShellCommand() = %q", got)
	}
}

func TestBuildProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		name := rapid.StringMatching("[a-z]{1,12}").Draw(t, "name")
		spec := Spec{Harness: "codex", Model: "gpt-6-sol", Effort: "high", WorktreePath: "/repo/work", BriefPath: "/brief", CredentialPath: "/seed", Group: "build", Name: name, BusURL: "nats://127.0.0.1:4222"}
		a, err := Build(spec)
		if err != nil {
			t.Fatal(err)
		}
		b, err := Build(spec)
		if err != nil || !reflect.DeepEqual(a, b) || a.Env["AGENTCTL_WORKER"] != name {
			t.Fatalf("nondeterministic recipe for %q", name)
		}
		command := ShellCommand([]string{name})
		if command != "exec '"+name+"'" {
			t.Fatalf("unsafe shell command %q", command)
		}
	})
}
