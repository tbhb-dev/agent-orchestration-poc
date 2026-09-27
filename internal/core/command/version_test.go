package command_test

import (
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/command"
)

func TestVersion(t *testing.T) {
	tests := []struct {
		name string
		args []string
		want string
		code int
	}{
		{"version", []string{"version"}, "agentd v1", 0},
		{"missing", nil, "usage: agentd version", 2},
		{"unknown", []string{"other"}, "usage: agentd version", 2},
		{"extra", []string{"version", "extra"}, "usage: agentd version", 2},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, code := command.Version(tt.args, "agentd", "v1")
			if got != tt.want || code != tt.code {
				t.Errorf("Version(%q) = (%q, %d), want (%q, %d)", tt.args, got, code, tt.want, tt.code)
			}
		})
	}
}
