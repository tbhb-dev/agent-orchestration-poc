// Package render turns command results into compact JSON and a short summary.
package render

import (
	"encoding/json/v2"
	"fmt"

	"github.com/tbhb/agent-orchestration-poc/internal/core/envelope"
	"github.com/tbhb/agent-orchestration-poc/internal/core/state"
)

// Result is the stable output shape shared by agentctl commands.
type Result struct {
	OK           bool                    `json:"ok"`
	Command      string                  `json:"command"`
	ID           string                  `json:"id,omitempty"`
	From         string                  `json:"from,omitempty"`
	To           string                  `json:"to,omitempty"`
	Message      *envelope.Message       `json:"message,omitempty"`
	Role         string                  `json:"role,omitempty"`
	Instructions string                  `json:"instructions,omitempty"`
	Status       string                  `json:"status,omitempty"`
	Detail       string                  `json:"detail,omitempty"`
	Roster       map[string]state.Roster `json:"roster,omitempty"`
	Error        string                  `json:"error,omitempty"`
}

// Render returns one newline-terminated JSON object and a human summary.
func Render(result Result) ([]byte, string, error) {
	body, err := json.Marshal(result)
	if err != nil {
		return nil, "", err
	}
	if result.Error != "" {
		return append(body, '\n'), result.Error, nil
	}
	summary := result.Command + " complete"
	if result.ID != "" {
		summary = fmt.Sprintf("%s %s", result.Command, result.ID)
	}
	return append(body, '\n'), summary, nil
}
