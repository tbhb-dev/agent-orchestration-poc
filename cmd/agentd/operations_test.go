package main

import (
	"context"
	"testing"
)

func TestRunOperationRejectsInvalidArguments(t *testing.T) {
	for _, tc := range []struct {
		name string
		args []string
	}{
		{"missing operation", nil},
		{"missing group action", []string{"group"}},
		{"invalid flag", []string{"list", "--invalid"}},
		{"missing state directory", []string{"list"}},
		{"positional argument", []string{"list", "--state-dir", t.TempDir(), "extra"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if err := runOperation(t.Context(), tc.args); err == nil {
				t.Fatalf("runOperation(%q) accepted invalid arguments", tc.args)
			}
		})
	}
}

func TestRunOperationReportsUnavailableDaemon(t *testing.T) {
	state := t.TempDir()
	for _, args := range [][]string{
		{"list", "--state-dir", state},
		{"group", "status", "--state-dir", state},
		{"spawn", "--state-dir", state, "--name", "standin", "--brief", "brief.md"},
	} {
		if err := runOperation(context.Background(), args); err == nil {
			t.Fatalf("runOperation(%q) succeeded without a daemon", args)
		}
	}
}
