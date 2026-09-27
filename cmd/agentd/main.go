// Command agentd is a placeholder that prints its version. The skeleton item
// adds no other behavior.
package main

import (
	"os"

	"github.com/tbhb/agent-orchestration-poc/internal/cli"
)

func main() {
	os.Exit(cli.Run("agentd", os.Args[1:], os.Stdout, os.Stderr))
}
