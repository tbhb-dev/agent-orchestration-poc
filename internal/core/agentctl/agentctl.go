// Package agentctl turns CLI arguments and relay responses into plain values.
package agentctl

import (
	"encoding/json/jsontext"
	"encoding/json/v2"
	"errors"
	"fmt"
	"strconv"
	"strings"

	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

// Defaults are environment values read by the command shell.
type Defaults struct{ Group, Agent, CredsFile, Port string }

// Command contains one validated operation and its connection settings.
type Command struct {
	Name, Group, Agent, CredsFile, To, Text, ID string
	Port, Timeout                               int
}

// Request is the authenticated relay request payload.
type Request struct {
	ID          string         `json:"id"`
	Destination string         `json:"destination,omitempty"`
	To          string         `json:"to,omitempty"`
	Envelope    jsontext.Value `json:"envelope,omitempty"`
	MessageID   string         `json:"message_id,omitempty"`
	Token       string         `json:"token,omitempty"`
	TimeoutMS   int            `json:"timeout_ms,omitzero"`
}

// Response is the daemon's bounded relay result.
type Response struct {
	Result   string         `json:"result"`
	Subject  string         `json:"subject,omitempty"`
	Token    string         `json:"token,omitempty"`
	Sequence uint64         `json:"sequence,omitzero"`
	Envelope jsontext.Value `json:"envelope,omitempty"`
}

// Output is one compact machine-readable result.
type Output struct {
	OK       bool           `json:"ok"`
	Command  string         `json:"command"`
	Result   string         `json:"result,omitempty"`
	ID       string         `json:"id,omitempty"`
	From     string         `json:"from,omitempty"`
	To       string         `json:"to,omitempty"`
	Sequence uint64         `json:"sequence,omitzero"`
	Message  jsontext.Value `json:"message,omitempty"`
	Error    string         `json:"error,omitempty"`
}

// Parse validates a command with its shell-provided defaults.
func Parse(args []string, defaults Defaults) (Command, error) {
	if len(args) == 0 {
		return Command{}, errors.New("missing command")
	}
	cmd := Command{Name: args[0], Group: defaults.Group, Agent: defaults.Agent, CredsFile: defaults.CredsFile, Timeout: 30}
	port := defaults.Port
	if port == "" {
		port = "4222"
	}
	positional, err := parseOptions(args[1:], &cmd, &port)
	if err != nil {
		return Command{}, err
	}
	cmd.Port, _ = strconv.Atoi(port)
	if cmd.Port < 1 || cmd.Port > 65535 || cmd.Timeout < 1 || cmd.Timeout > 3600 {
		return Command{}, errors.New("invalid port or timeout")
	}
	if layout.ValidToken(cmd.Group) != nil || layout.ValidAgent(cmd.Agent) != nil || cmd.CredsFile == "" {
		return Command{}, errors.New("group, agent, and credential file are required")
	}
	return setPositionals(cmd, positional)
}

func parseOptions(args []string, cmd *Command, port *string) ([]string, error) {
	var positional []string
	for len(args) > 0 {
		argument := args[0]
		args = args[1:]
		if !strings.HasPrefix(argument, "--") {
			positional = append(positional, argument)
			continue
		}
		if len(args) == 0 {
			return nil, fmt.Errorf("%s requires a value", argument)
		}
		if err := applyOption(cmd, port, argument, args[0]); err != nil {
			return nil, err
		}
		args = args[1:]
	}
	return positional, nil
}

func applyOption(cmd *Command, port *string, flag, value string) error {
	switch flag {
	case "--group":
		cmd.Group = value
	case "--agent":
		cmd.Agent = value
	case "--creds-file":
		cmd.CredsFile = value
	case "--port":
		*port = value
	case "--timeout":
		if cmd.Name != "receive" {
			return errors.New("--timeout requires receive")
		}
		cmd.Timeout, _ = strconv.Atoi(value)
	case "--id":
		if cmd.Name != "send" || layout.ValidToken(value) != nil {
			return errors.New("invalid send ID")
		}
		cmd.ID = value
	default:
		return fmt.Errorf("unknown option %s", flag)
	}
	return nil
}

func setPositionals(cmd Command, positional []string) (Command, error) {
	switch cmd.Name {
	case "send":
		if len(positional) != 2 || positional[1] == "" || len(positional[1]) > 8192 {
			return Command{}, errors.New("send requires <to> and 1 to 8192 bytes of text")
		}
		cmd.To, cmd.Text = positional[0], positional[1]
		if cmd.To != "*" && cmd.To != "operator" && layout.ValidAgent(cmd.To) != nil {
			return Command{}, errors.New("invalid recipient")
		}
	case "ack":
		if len(positional) != 1 || positional[0] == "" {
			return Command{}, errors.New("ack requires a delivery token")
		}
		cmd.ID = positional[0]
	case "receive":
		if len(positional) != 0 {
			return Command{}, errors.New("receive accepts no arguments")
		}
	default:
		return Command{}, errors.New("unsupported command")
	}
	return cmd, nil
}

// Payload maps a command to a request without broker effects.
func Payload(cmd Command, requestID, messageID string, waitMS int) (Request, error) {
	request := Request{ID: requestID}
	switch cmd.Name {
	case "send":
		request.MessageID = messageID
		request.To = cmd.To
		switch cmd.To {
		case "*":
			request.Destination, request.To = "all", ""
		case "operator":
			request.Destination, request.To = "operator", ""
		default:
			request.Destination = "dm"
		}
		data, err := json.Marshal(struct {
			Body struct {
				Text string `json:"text"`
			} `json:"body"`
		}{Body: struct {
			Text string `json:"text"`
		}{Text: cmd.Text}})
		request.Envelope = data
		return request, err
	case "receive":
		request.TimeoutMS = waitMS
	case "ack":
		request.Token = cmd.ID
	}
	return request, nil
}

// WaitMS caps one relay pull while preserving the requested deadline.
func WaitMS(remaining int) int {
	if remaining > 5000 {
		return 5000
	}
	if remaining < 1 {
		return 1
	}
	return remaining
}

// Interpret maps relay outcomes to output and CLI exit status.
func Interpret(cmd Command, response Response, messageID string) (Output, int) {
	out := Output{Command: cmd.Name, Result: response.Result}
	switch cmd.Name {
	case "send":
		if response.Result == "stored" || response.Result == "duplicate" {
			out.OK, out.ID, out.To, out.Sequence = true, messageID, cmd.To, response.Sequence
		}
	case "receive":
		if response.Result == "delivered" && response.Token != "" && response.Envelope.IsValid() {
			out.OK, out.ID, out.Message, out.Sequence = true, response.Token, response.Envelope, response.Sequence
			out.From = Sender(response.Subject)
		}
		if response.Result == "empty" {
			return out, 3
		}
	case "ack":
		if response.Result == "acked" {
			out.OK, out.ID = true, cmd.ID
		}
	}
	if out.OK {
		return out, 0
	}
	out.Error = response.Result
	return out, 1
}

// Sender extracts the attributed sender from a relay delivery subject.
func Sender(subject string) string {
	parts := strings.Split(subject, ".")
	if len(parts) == 6 && parts[0] == "grp" && parts[2] == "msg" && parts[3] == "dm" {
		return parts[5]
	}
	if len(parts) == 5 && parts[0] == "grp" && parts[2] == "msg" && (parts[3] == "all" || parts[3] == "op") {
		return parts[4]
	}
	return ""
}
