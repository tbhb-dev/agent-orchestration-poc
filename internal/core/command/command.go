// Package command parses agentctl arguments into values without reading the environment.
package command

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

// Value is a parsed agentctl action.
type Value struct {
	Name          string
	Group         string
	Agent         string
	CredsFile     string
	Port          int
	PortExplicit  bool
	To            string
	Text          string
	ID            string
	CorrelationID string
	ReplyToID     string
	Wait          time.Duration
	Timeout       time.Duration
	Set           string
	Detail        string
}

// Defaults are environment values obtained by the shell.
type Defaults struct {
	Group     string
	Agent     string
	CredsFile string
	Port      string
}

// Parse turns arguments into a command or a usage error.
func Parse(args []string) (Value, error) {
	if len(args) == 0 {
		return Value{}, errors.New("missing command")
	}
	value := Value{Name: args[0], Port: 4222, Timeout: 30 * time.Second}
	var positional []string
	for i := 1; i < len(args); i++ {
		arg := args[i]
		if !strings.HasPrefix(arg, "--") {
			positional = append(positional, arg)
			continue
		}
		if i+1 == len(args) {
			return Value{}, fmt.Errorf("%s requires a value", arg)
		}
		i++
		if err := setFlag(&value, arg, args[i]); err != nil {
			return Value{}, err
		}
	}
	if err := setPositionals(&value, positional); err != nil {
		return Value{}, err
	}
	return value, validate(value)
}

func setFlag(value *Value, flag, argument string) error {
	switch flag {
	case "--group":
		value.Group = argument
	case "--agent":
		value.Agent = argument
	case "--creds-file":
		value.CredsFile = argument
	case "--port", "--wait", "--timeout":
		return setNumericFlag(value, flag, argument)
	case "--set":
		value.Set = argument
	case "--detail":
		value.Detail = argument
	case "--id":
		value.ID = argument
	case "--correlation-id":
		value.CorrelationID = argument
	case "--reply-to-id":
		value.ReplyToID = argument
	default:
		return fmt.Errorf("unknown flag %s", flag)
	}
	return nil
}

func setNumericFlag(value *Value, flag, argument string) error {
	number, err := strconv.Atoi(argument)
	if err != nil {
		return fmt.Errorf("%s requires a number", flag)
	}
	if flag == "--port" {
		if number < 1 || number > 65535 {
			return errors.New("port must be from 1 to 65535")
		}
		value.Port = number
		value.PortExplicit = true
		return nil
	}
	if number < 1 || number > 3600 {
		return fmt.Errorf("%s must be from 1 to 3600 seconds", flag)
	}
	if flag == "--wait" {
		value.Wait = time.Duration(number) * time.Second
	} else {
		value.Timeout = time.Duration(number) * time.Second
	}
	return nil
}

func setPositionals(value *Value, args []string) error {
	switch value.Name {
	case "send":
		if len(args) != 2 {
			return errors.New("send requires <to> <text>")
		}
		value.To, value.Text = args[0], args[1]
	case "ack":
		if len(args) != 1 {
			return errors.New("ack requires <id>")
		}
		value.ID = args[0]
	case "join", "receive", "status", "roster", "version", "help":
		if len(args) != 0 {
			return fmt.Errorf("%s accepts no positional arguments", value.Name)
		}
	default:
		return fmt.Errorf("unknown command %s", value.Name)
	}
	return nil
}

func validate(value Value) error {
	if value.Name == "send" {
		if value.Text == "" {
			return errors.New("text is required")
		}
		if value.To != "*" && value.To != "operator" {
			return layout.ValidAgent(value.To)
		}
	}
	if value.Name == "status" {
		if value.Set != "" && value.Set != "working" && value.Set != "idle" && value.Set != "blocked" {
			return errors.New("status must be working, idle, or blocked")
		}
		if value.Detail != "" && value.Set == "" {
			return errors.New("--detail requires --set")
		}
	}
	return nil
}

// Resolve applies shell-provided defaults and validates the identity.
func Resolve(value Value, defaults Defaults) (Value, error) {
	if value.Group == "" {
		value.Group = defaults.Group
	}
	if value.Agent == "" {
		value.Agent = defaults.Agent
	}
	if value.CredsFile == "" {
		value.CredsFile = defaults.CredsFile
	}
	if defaults.Port != "" && !value.PortExplicit {
		port, err := strconv.Atoi(defaults.Port)
		if err != nil || port < 1 || port > 65535 {
			return Value{}, errors.New("invalid AGENTCTL_PORT")
		}
		value.Port = port
	}
	if value.Name == "version" || value.Name == "help" {
		return value, nil
	}
	if err := validateIdentity(value); err != nil {
		return Value{}, err
	}
	return value, nil
}

func validateIdentity(value Value) error {
	if err := layout.ValidToken(value.Group); err != nil {
		return fmt.Errorf("group: %w", err)
	}
	if value.Agent != "operator" {
		if err := layout.ValidAgent(value.Agent); err != nil {
			return fmt.Errorf("agent: %w", err)
		}
	}
	if value.CredsFile == "" {
		return errors.New("credential file path is required")
	}
	if value.Name == "ack" && !ValidAckSubject(value, value.ID) {
		return errors.New("ack ID is not for this agent's consumer")
	}
	return nil
}

// Subject returns the permitted message route for a send command.
func Subject(value Value) (string, error) {
	switch value.To {
	case "*":
		return layout.Broadcast(value.Group, value.Agent)
	case "operator":
		return layout.Operator(value.Group, value.Agent)
	default:
		return layout.Direct(value.Group, value.To, value.Agent)
	}
}

// Kind selects the envelope kind from the requested send behavior.
func Kind(value Value) string {
	if value.ReplyToID != "" || value.CorrelationID != "" {
		return "answer"
	}
	if value.Wait > 0 {
		return "question"
	}
	return "message"
}

// ReplyFilter selects the live subscription used by send --wait.
func ReplyFilter(value Value) (string, error) {
	if value.Agent == "operator" {
		stream, err := layout.Stream(value.Group)
		if err != nil {
			return "", err
		}
		return stream.Subjects[0], nil
	}
	filters, err := layout.ConsumerFilters(value.Group, value.Agent)
	if err != nil {
		return "", err
	}
	return filters[1], nil
}

// ValidAckSubject restricts an ack token to this agent's durable consumer.
func ValidAckSubject(value Value, subject string) bool {
	stream, err := layout.Stream(value.Group)
	if err != nil {
		return false
	}
	consumer, err := layout.Consumer(value.Group, value.Agent)
	if err != nil {
		return false
	}
	return strings.HasPrefix(subject, "$JS.ACK."+stream.Name+"."+consumer.Name+".")
}

// Sender reads the final subject token, where the layout places the sender.
func Sender(subject string) string {
	index := strings.LastIndexByte(subject, '.')
	if index < 0 {
		return ""
	}
	return subject[index+1:]
}

// Role is the initial roster role for an identity.
func Role(value Value) string {
	if value.Agent == "operator" {
		return "operator"
	}
	return "worker"
}

// JoinInstructions gives the worker the minimal receive and ack loop.
func JoinInstructions() string {
	return "Run agentctl receive to wait for work, then agentctl ack <id>."
}
