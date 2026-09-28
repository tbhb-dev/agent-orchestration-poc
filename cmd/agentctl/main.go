package main

import (
	"encoding/json/v2"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/cli"
	"github.com/tbhb/agent-orchestration-poc/internal/core/agentctl"
)

const help = `agentctl send <to> <text> [--id ID]
agentctl receive [--timeout SECONDS]
agentctl ack <delivery-token>

Common options: --group NAME --agent NAME --creds-file PATH --port PORT
Defaults: AGENTCTL_GROUP, AGENTCTL_AGENT, AGENTCTL_CREDS_FILE, AGENTCTL_PORT
Receive timeout: 1 to 3600 seconds (default 30).
Output: one compact JSON object per line; receive.id is an opaque relay token.
Exit codes: 0 success, 1 relay error, 2 usage error, 3 receive timeout.
`

func main() { os.Exit(run(os.Args[1:], os.Stdout)) }

func run(args []string, output io.Writer) int {
	if len(args) == 1 && args[0] == "version" {
		return cli.Run("agentctl", args, "usage: agentctl version", output, os.Stderr)
	}
	if len(args) == 1 && (args[0] == "--help" || args[0] == "help") {
		_, _ = io.WriteString(output, help)
		return 0
	}
	cmd, err := agentctl.Parse(args, agentctl.Defaults{
		Group: os.Getenv("AGENTCTL_GROUP"), Agent: os.Getenv("AGENTCTL_AGENT"),
		CredsFile: os.Getenv("AGENTCTL_CREDS_FILE"), Port: os.Getenv("AGENTCTL_PORT"),
	})
	if err != nil {
		return fail(output, "usage", err, 2)
	}
	connection, err := Connect(cmd)
	if err != nil {
		return fail(output, cmd.Name, err, 1)
	}
	defer connection.Close()
	return execute(connection, cmd, output)
}

func execute(connection *Client, cmd agentctl.Command, output io.Writer) int {
	messageID := cmd.ID
	if cmd.Name == "send" && messageID == "" {
		var err error
		messageID, err = NewID()
		if err != nil {
			return fail(output, cmd.Name, err, 1)
		}
	}
	deadline := time.Now().Add(time.Duration(cmd.Timeout) * time.Second)
	for {
		response, err := callOnce(connection, cmd, messageID, deadline)
		if err != nil {
			return fail(output, cmd.Name, err, 1)
		}
		result, code := agentctl.Interpret(cmd, response, messageID)
		if cmd.Name != "receive" || response.Result != "empty" || time.Until(deadline) <= 0 {
			write(output, result)
			return code
		}
	}
}

func callOnce(connection *Client, cmd agentctl.Command, messageID string, deadline time.Time) (agentctl.Response, error) {
	requestID, err := NewID()
	if err != nil {
		return agentctl.Response{}, err
	}
	wait := 0
	if cmd.Name == "receive" {
		wait = agentctl.WaitMS(int(time.Until(deadline).Milliseconds()))
	}
	request, err := agentctl.Payload(cmd, requestID, messageID, wait)
	if err != nil {
		return agentctl.Response{}, err
	}
	return connection.Call(cmd, request)
}

func fail(output io.Writer, command string, err error, code int) int {
	write(output, agentctl.Output{Command: command, Error: err.Error()})
	return code
}

func write(output io.Writer, value agentctl.Output) {
	data, err := json.Marshal(value)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return
	}
	_, _ = output.Write(append(data, '\n'))
}
