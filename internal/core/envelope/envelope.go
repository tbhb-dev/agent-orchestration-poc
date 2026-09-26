// Package envelope validates and encodes agent messages without broker effects.
package envelope

import (
	"encoding/json/v2"
	"errors"
	"fmt"
	"strings"
)

const (
	MaxTextBytes = 8192
	MaxBodyBytes = 16384
)

// Body is the JSON payload carried by a bus message.
type Body struct {
	Text             string         `json:"text"`
	Refs             map[string]int `json:"refs,omitempty"`
	HarnessSessionID string         `json:"harness_session_id,omitempty"`
}

// Headers are supplied by the shell, including its clock and identifier.
type Headers struct {
	ID            string `json:"id"`
	CorrelationID string `json:"correlation_id,omitempty"`
	ReplyToID     string `json:"reply_to_id,omitempty"`
	Kind          string `json:"kind"`
	Timestamp     string `json:"timestamp"`
}

// Message contains a validated body and its metadata.
type Message struct {
	Body    Body    `json:"body"`
	Headers Headers `json:"headers"`
}

// Validate checks the payload and header limits before publication.
func Validate(message Message) error {
	if message.Body.Text == "" || len(message.Body.Text) > MaxTextBytes {
		return fmt.Errorf("text must contain 1 to %d bytes", MaxTextBytes)
	}
	if message.Headers.ID == "" || message.Headers.Timestamp == "" ||
		!validHeaderValue(message.Headers.ID) || !validHeaderValue(message.Headers.Timestamp) {
		return errors.New("message ID and timestamp are required")
	}
	if !validHeaderValue(message.Headers.CorrelationID) || !validHeaderValue(message.Headers.ReplyToID) {
		return errors.New("invalid correlation or reply ID")
	}
	switch message.Headers.Kind {
	case "message", "question", "answer", "event":
	default:
		return errors.New("kind must be message, question, answer, or event")
	}
	for key, value := range message.Body.Refs {
		if key == "" || strings.ContainsAny(key, "\r\n") || value < 1 {
			return errors.New("invalid reference")
		}
	}
	return nil
}

func validHeaderValue(value string) bool {
	return !strings.ContainsAny(value, "\r\n") && len(value) <= 256
}

// Encode returns a body and plain header map for publication.
func Encode(message Message) ([]byte, map[string]string, error) {
	if err := Validate(message); err != nil {
		return nil, nil, err
	}
	body, err := json.Marshal(message.Body)
	if err != nil {
		return nil, nil, err
	}
	if len(body) > MaxBodyBytes {
		return nil, nil, errors.New("message body is too large")
	}
	return body, map[string]string{
		"Nats-Msg-Id":    message.Headers.ID,
		"Correlation-Id": message.Headers.CorrelationID,
		"Reply-To-Id":    message.Headers.ReplyToID,
		"Kind":           message.Headers.Kind,
		"Timestamp":      message.Headers.Timestamp,
	}, nil
}

// Decode checks an incoming byte payload and plain header map.
func Decode(body []byte, headers map[string]string) (Message, error) {
	if len(body) > MaxBodyBytes {
		return Message{}, errors.New("message body is too large")
	}
	message := Message{Headers: Headers{
		ID: headers["Nats-Msg-Id"], CorrelationID: headers["Correlation-Id"],
		ReplyToID: headers["Reply-To-Id"], Kind: headers["Kind"], Timestamp: headers["Timestamp"],
	}}
	if err := json.Unmarshal(body, &message.Body); err != nil {
		return Message{}, err
	}
	if err := Validate(message); err != nil {
		return Message{}, err
	}
	return message, nil
}

// IsReplyTo matches an answer to the original message ID.
func IsReplyTo(message Message, id string) bool {
	return id != "" && message.Headers.Kind == "answer" && message.Headers.CorrelationID == id
}
