package provision

import (
	"bytes"
	"context"
	"encoding/json/v2"
	"fmt"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/roster"
)

// Request is the local daemon API mounted by agentd and later by agentctl.
type Request struct {
	Operation, Name string
	Spawn           SpawnRequest
	Lines           int
}

// Response contains the result of one operation.
type Response struct {
	Worker         roster.Worker
	Workers        []roster.Worker
	Status         Status
	Capture, Error string
}

// Handle maps local requests onto provisioner operations.
func (s *Service) Handle(ctx context.Context, req Request) (out Response) {
	var err error
	switch req.Operation {
	case "spawn":
		out.Worker, err = s.Spawn(ctx, req.Spawn)
	case "list":
		out.Workers, err = s.List(ctx)
	case "capture":
		out.Capture, err = s.Capture(ctx, req.Name, req.Lines)
	case "nudge":
		err = s.Nudge(ctx, req.Name)
	case "stop":
		out.Worker, err = s.Stop(ctx, req.Name)
	case "group-start":
		out.Status.Group, err = s.GroupStart(ctx)
	case "group-stop":
		out.Status.Group, err = s.GroupStop(ctx)
	case "group-status":
		out.Status, err = s.GroupStatus(ctx)
	default:
		err = fmt.Errorf("unknown operation %q", req.Operation)
	}
	if err != nil {
		out.Error = err.Error()
	}
	return out
}

// ServeLocal exposes operations only on a mode-0600 Unix socket.
func (s *Service) ServeLocal(ctx context.Context) error {
	path := filepath.Join(s.StateDir, "agentd.sock")
	listener, err := net.Listen("unix", path)
	if err != nil {
		return err
	}
	defer func() { _ = listener.Close() }()
	defer func() { _ = os.Remove(path) }()
	if err := os.Chmod(path, 0o600); err != nil {
		return err
	}
	mux := http.NewServeMux()
	mux.HandleFunc("POST /operation", func(w http.ResponseWriter, r *http.Request) {
		var req Request
		if err := json.UnmarshalRead(r.Body, &req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if err := json.MarshalWrite(w, s.Handle(r.Context(), req)); err != nil {
			return
		}
	})
	server := &http.Server{Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() { <-ctx.Done(); _ = server.Close() }()
	if err := server.Serve(listener); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

// Call sends one local request to the running daemon.
func Call(ctx context.Context, stateDir string, req Request) (Response, error) {
	path := filepath.Join(stateDir, "agentd.sock")
	transport := &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", path)
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport}
	data, err := json.Marshal(req)
	if err != nil {
		return Response{}, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, "http://unix/operation", bytes.NewReader(data))
	if err != nil {
		return Response{}, err
	}
	resp, err := client.Do(httpReq)
	if err != nil {
		return Response{}, err
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode != http.StatusOK {
		return Response{}, fmt.Errorf("agentd returned %s", resp.Status)
	}
	var out Response
	if err := json.UnmarshalRead(resp.Body, &out); err != nil {
		return out, err
	}
	if out.Error != "" {
		return out, fmt.Errorf("%s", out.Error)
	}
	return out, nil
}
