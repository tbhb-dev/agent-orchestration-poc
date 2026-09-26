// Command agentctl exchanges messages and status with an embedded agentd bus.
package main

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/tbhb/agent-orchestration-poc/internal/bus/client"
	"github.com/tbhb/agent-orchestration-poc/internal/core/command"
	"github.com/tbhb/agent-orchestration-poc/internal/core/render"
	"github.com/tbhb/agent-orchestration-poc/internal/version"
)

const help = `agentctl [join|send|receive|ack|status|roster] [options]

  join                                      Register this agent and show roster
  send <to> <text> [--wait N]                Send to agent, *, or operator
  receive [--timeout N]                     Fetch one durable message
  ack <id>                                  Acknowledge a received message
  status [--set working|idle|blocked --detail TEXT]
  roster                                    Show joined agents

Common options after the command: --group NAME --agent NAME --creds-file PATH --port PORT
Defaults: AGENTCTL_GROUP, AGENTCTL_AGENT, AGENTCTL_CREDS_FILE, AGENTCTL_PORT
Send options: --id ID --correlation-id ID --reply-to-id ID
N and timeout are whole seconds from 1 to 3600.

Output: one JSON object per line on stdout, short summary on stderr.
Stable fields: ok, command, id, from, to, message, role, instructions,
status, detail, roster, error. Optional fields are omitted when empty.
Receive id is the broker ack token. Pass that exact value to ack.
Exit codes: 0 success, 1 bus error, 2 usage error, 3 timeout with no message.
The credential value is read only from the named file and is never printed.
`

func main() { os.Exit(run(os.Args[1:])) }

func run(args []string) int {
	if len(args) == 1 && (args[0] == "--help" || args[0] == "help") {
		fmt.Print(help)
		return 0
	}
	value, err := command.Parse(args)
	if err != nil {
		printResult(render.Result{OK: false, Command: "usage", Error: err.Error()})
		return 2
	}
	if value.Name == "version" {
		printResult(render.Result{OK: true, Command: "version", Detail: version.String()})
		return 0
	}
	value, err = command.Resolve(value, command.Defaults{
		Group: os.Getenv("AGENTCTL_GROUP"), Agent: os.Getenv("AGENTCTL_AGENT"),
		CredsFile: os.Getenv("AGENTCTL_CREDS_FILE"), Port: os.Getenv("AGENTCTL_PORT"),
	})
	if err != nil {
		printResult(render.Result{OK: false, Command: "usage", Error: err.Error()})
		return 2
	}
	conn, err := client.Connect(value)
	if err == nil {
		defer conn.Close()
		var result render.Result
		result, err = conn.Run(context.Background(), value)
		if err == nil {
			printResult(result)
			return 0
		}
	}
	code := 1
	if errors.Is(err, client.ErrTimeout) {
		code = 3
	}
	printResult(render.Result{OK: false, Command: value.Name, Error: err.Error()})
	return code
}

func printResult(result render.Result) {
	line, summary, err := render.Render(result)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return
	}
	_, _ = os.Stdout.Write(line)
	fmt.Fprintln(os.Stderr, summary)
}
