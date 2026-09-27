//go:build integration

package main

import (
	"strings"
	"testing"
)

func TestAgentsFlag(t *testing.T) {
	var agents agentsFlag
	if err := agents.Set("first"); err != nil {
		t.Fatal(err)
	}
	if err := agents.Set("second"); err != nil {
		t.Fatal(err)
	}
	if got := agents.String(); got != "first,second" {
		t.Errorf("String() = %q, want first,second", got)
	}
}

func TestServeRejectsInvalidArguments(t *testing.T) {
	for _, tt := range []struct {
		name string
		args []string
	}{
		{"missing state", nil},
		{"invalid port", []string{"--state-dir", t.TempDir(), "--port", "65536"}},
		{"positional argument", []string{"--state-dir", t.TempDir(), "extra"}},
		{"unknown flag", []string{"--unknown"}},
	} {
		t.Run(tt.name, func(t *testing.T) {
			if err := serve(tt.args); err == nil {
				t.Errorf("serve(%q) succeeded, want error", tt.args)
			}
		})
	}
}

func TestServeRejectsInvalidAgent(t *testing.T) {
	err := serve([]string{"--state-dir", t.TempDir(), "--port", "4222", "--agent", "Invalid"})
	if err == nil || !strings.Contains(err.Error(), "Invalid") {
		t.Errorf("serve() error = %v, want invalid agent", err)
	}
}
