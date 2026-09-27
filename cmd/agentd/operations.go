package main

import (
	"context"
	"encoding/json/v2"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/tbhb/agent-orchestration-poc/internal/provision"
)

func serveWithOperations(ctx context.Context, state string, port int, agents []string) error {
	command := exec.CommandContext(ctx, "git", "rev-parse", "--path-format=absolute", "--git-common-dir")
	output, err := command.Output()
	if err != nil {
		return fmt.Errorf("resolve git common directory: %w", err)
	}
	gitDir := strings.TrimSpace(string(output))
	service, err := provision.Open(ctx, state, gitDir, port, agents)
	if err != nil {
		return err
	}
	defer func() { _ = service.Close() }()
	fmt.Println("bus ready at", service.Bus.URL())
	fmt.Println("credentials under", filepath.Join(state, "bus"))
	return service.ServeLocal(ctx)
}

func runOperation(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return errors.New("missing operation")
	}
	op := args[0]
	if op == "group" {
		if len(args) < 2 {
			return errors.New("group requires start, stop, or status")
		}
		op = "group-" + args[1]
		args = args[1:]
	}
	flags := flag.NewFlagSet(op, flag.ContinueOnError)
	state := flags.String("state-dir", "", "agentd state directory")
	name := flags.String("name", "", "worker name")
	harness := flags.String("harness", "", "claude, codex, or agy")
	model := flags.String("model", "", "explicit model id")
	effort := flags.String("effort", "", "explicit effort level")
	issue := flags.Int("issue", 0, "issue number")
	kind := flags.String("type", "feat", "branch type")
	slug := flags.String("slug", "", "branch slug")
	brief := flags.String("brief", "", "source brief file")
	lines := flags.Int("lines", 100, "capture line count")
	if err := flags.Parse(args[1:]); err != nil {
		return err
	}
	if *state == "" || flags.NArg() != 0 {
		return errors.New("operation requires --state-dir and no positional arguments")
	}
	req := provision.Request{Operation: op, Name: *name, Lines: *lines}
	if op == "spawn" {
		absoluteBrief, err := filepath.Abs(*brief)
		if err != nil {
			return err
		}
		req.Spawn = provision.SpawnRequest{
			Name: *name, Harness: *harness, Model: *model, Effort: *effort,
			Issue: *issue, Kind: *kind, Slug: *slug, BriefPath: absoluteBrief,
		}
	}
	response, err := provision.Call(ctx, *state, req)
	if err != nil {
		return err
	}
	if err := json.MarshalWrite(os.Stdout, response); err != nil {
		return err
	}
	fmt.Println()
	return nil
}
