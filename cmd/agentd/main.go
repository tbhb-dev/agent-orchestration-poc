// Command agentd runs the embedded bus for the build group.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/tbhb/agent-orchestration-poc/internal/cli"
)

type agentsFlag []string

func (a *agentsFlag) String() string { return strings.Join(*a, ",") }
func (a *agentsFlag) Set(name string) error {
	*a = append(*a, name)
	return nil
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "serve" {
		if err := serve(os.Args[2:]); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "spawn", "list", "capture", "nudge", "stop", "group":
			if err := runOperation(context.Background(), os.Args[1:]); err != nil {
				fmt.Fprintln(os.Stderr, err)
				os.Exit(1)
			}
			return
		}
	}
	os.Exit(cli.Run("agentd", os.Args[1:], "usage: agentd version | serve --state-dir DIR [--port PORT] [--agent NAME ...] | spawn|list|capture|nudge|stop|group ...", os.Stdout, os.Stderr))
}

func serve(args []string) error {
	flags := flag.NewFlagSet("serve", flag.ContinueOnError)
	state := flags.String("state-dir", "", "directory for JetStream and credential files")
	port := flags.Int("port", 4222, "IPv4 loopback port")
	var agents agentsFlag
	flags.Var(&agents, "agent", "initial agent name, repeatable")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *state == "" || flags.NArg() != 0 || *port < 1 || *port > 65535 {
		return errors.New("serve requires --state-dir and a valid --port")
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	return serveWithOperations(ctx, *state, *port, agents)
}
