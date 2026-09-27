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

	"github.com/tbhb/agent-orchestration-poc/internal/version"
)

type agentsFlag []string

func (a *agentsFlag) String() string { return strings.Join(*a, ",") }
func (a *agentsFlag) Set(name string) error {
	*a = append(*a, name)
	return nil
}

func main() {
	if len(os.Args) == 2 && os.Args[1] == "version" {
		fmt.Println("agentd", version.String())
		return
	}
	if len(os.Args) > 1 {
		var err error
		switch os.Args[1] {
		case "serve":
			err = serve(os.Args[2:])
		case "spawn", "list", "capture", "nudge", "stop", "group":
			err = runOperation(context.Background(), os.Args[1:])
		default:
			fmt.Fprintln(os.Stderr, "usage: agentd version | serve --state-dir DIR [--port PORT] [--agent NAME ...] | spawn|list|capture|nudge|stop|group ...")
			os.Exit(2)
		}
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	fmt.Fprintln(os.Stderr, "usage: agentd version | serve --state-dir DIR [--port PORT] [--agent NAME ...] | spawn|list|capture|nudge|stop|group ...")
	os.Exit(2)
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
