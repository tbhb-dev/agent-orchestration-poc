// Package cli writes command responses to the matching output stream.
package cli

import (
	"fmt"
	"io"

	"github.com/tbhb/agent-orchestration-poc/internal/core/command"
	"github.com/tbhb/agent-orchestration-poc/internal/version"
)

// Run writes a version command response and returns its exit code.
func Run(name string, args []string, usage string, stdout, stderr io.Writer) int {
	message, code := command.Version(args, name, version.String(), usage)
	if code == 0 {
		if _, err := fmt.Fprintln(stdout, message); err != nil {
			return 1
		}
	} else {
		if _, err := fmt.Fprintln(stderr, message); err != nil {
			return 1
		}
	}
	return code
}
