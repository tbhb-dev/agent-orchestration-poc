// Package state encodes the bootstrap roster and status bucket values.
package state

import (
	"encoding/json/v2"
	"errors"
)

const MaxValueBytes = 4096

// Status records one agent's last reported work state.
type Status struct {
	State     string `json:"state"`
	Detail    string `json:"detail,omitempty"`
	UpdatedAt string `json:"updated_at"`
}

// Roster records the identity known at join time.
type Roster struct {
	Role     string `json:"role"`
	JoinedAt string `json:"joined_at"`
}

// EncodeStatus validates and serializes a status value.
func EncodeStatus(value Status) ([]byte, error) {
	if value.State != "working" && value.State != "idle" && value.State != "blocked" {
		return nil, errors.New("invalid status")
	}
	if value.UpdatedAt == "" || len(value.Detail) > MaxValueBytes {
		return nil, errors.New("invalid status detail or timestamp")
	}
	return encode(value)
}

// DecodeStatus validates a stored status value.
func DecodeStatus(data []byte) (Status, error) {
	var value Status
	if len(data) > MaxValueBytes {
		return value, errors.New("status value is too large")
	}
	if err := json.Unmarshal(data, &value); err != nil {
		return value, err
	}
	_, err := EncodeStatus(value)
	return value, err
}

// EncodeRoster validates and serializes a roster value.
func EncodeRoster(value Roster) ([]byte, error) {
	if value.Role == "" || value.JoinedAt == "" {
		return nil, errors.New("role and joined time are required")
	}
	return encode(value)
}

// DecodeRoster validates a stored roster value.
func DecodeRoster(data []byte) (Roster, error) {
	var value Roster
	if len(data) > MaxValueBytes {
		return value, errors.New("roster value is too large")
	}
	if err := json.Unmarshal(data, &value); err != nil {
		return value, err
	}
	_, err := EncodeRoster(value)
	return value, err
}

func encode(value any) ([]byte, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	if len(data) > MaxValueBytes {
		return nil, errors.New("value is too large")
	}
	return data, nil
}
