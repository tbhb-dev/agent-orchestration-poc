package cli_test

import (
	"bytes"
	"errors"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/cli"
)

type errorWriter struct{}

func (errorWriter) Write([]byte) (int, error) {
	return 0, errors.New("write failed")
}

func TestRun(t *testing.T) {
	for _, tt := range []struct {
		name   string
		args   []string
		stdout string
		stderr string
		code   int
	}{
		{"agentd", []string{"version"}, "agentd dev\n", "", 0},
		{"agentctl", nil, "", "usage: agentctl version\n", 2},
	} {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := cli.Run(tt.name, tt.args, &stdout, &stderr)
			if code != tt.code || stdout.String() != tt.stdout || stderr.String() != tt.stderr {
				t.Errorf("Run() = (%q, %q, %d), want (%q, %q, %d)", stdout.String(), stderr.String(), code, tt.stdout, tt.stderr, tt.code)
			}
		})
	}
}

func TestRunWriteFailure(t *testing.T) {
	var output bytes.Buffer
	if code := cli.Run("agentd", []string{"version"}, errorWriter{}, &output); code != 1 {
		t.Errorf("stdout failure code = %d, want 1", code)
	}
	if code := cli.Run("agentd", nil, &output, errorWriter{}); code != 1 {
		t.Errorf("stderr failure code = %d, want 1", code)
	}
}
