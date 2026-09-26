// Command agentctl is a placeholder that prints its version. The skeleton item
// adds no other behavior.
package main

import (
	"fmt"
	"os"

	"github.com/tbhb/agent-orchestration-poc/internal/version"
)

func main() {
	if len(os.Args) == 2 && os.Args[1] == "version" {
		fmt.Println("agentctl", version.String())
		return
	}
	fmt.Fprintln(os.Stderr, "usage: agentctl version")
	os.Exit(2)
}
