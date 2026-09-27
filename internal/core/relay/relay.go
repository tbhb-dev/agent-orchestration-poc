// Package relay validates relay subjects and turns requests into broker values.
package relay

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json/jsontext"
	"errors"
	"strings"

	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

var operations = map[string]bool{"send": true, "receive": true, "ack": true, "status": true, "roster": true}

// Request identifies the authenticated account, operation, and agent.
type Request struct {
	Group     string
	Operation string
	Agent     string
}

// ParseRequest accepts only the complete request grammar for one account.
func ParseRequest(account, subject string) (Request, error) {
	parts := strings.Split(subject, ".")
	if len(parts) != 6 || parts[0] != "grp" || parts[2] != "relay" || parts[3] != "req" || parts[1] != account || !operations[parts[4]] {
		return Request{}, errors.New("invalid relay request subject")
	}
	if layout.ValidToken(account) != nil || layout.ValidAgent(parts[5]) != nil {
		return Request{}, errors.New("invalid relay request identity")
	}
	return Request{Group: account, Operation: parts[4], Agent: parts[5]}, nil
}

// Reply builds the only response namespace for the authenticated agent.
func Reply(req Request, id string) (string, error) {
	if layout.ValidToken(req.Group) != nil || layout.ValidAgent(req.Agent) != nil || layout.ValidToken(id) != nil {
		return "", errors.New("invalid relay reply token")
	}
	return "grp." + req.Group + ".relay.reply." + req.Agent + "." + id, nil
}

// SendSubject derives the sender from the authenticated request subject.
func SendSubject(req Request, destination, to string) (string, error) {
	switch destination {
	case "all":
		if to != "" {
			break
		}
		return layout.Broadcast(req.Group, req.Agent)
	case "dm":
		return layout.Direct(req.Group, to, req.Agent)
	case "operator":
		if to != "" {
			break
		}
		return layout.Operator(req.Group, req.Agent)
	}
	return "", errors.New("invalid relay destination")
}

// MessageID scopes a client id to the authenticated publication identity.
func MessageID(req Request, subject, id string) (string, error) {
	if id == "" {
		return "", nil
	}
	if layout.ValidToken(id) != nil {
		return "", errors.New("invalid message id")
	}
	if !strings.HasPrefix(subject, "grp."+req.Group+".msg.") || !strings.HasSuffix(subject, "."+req.Agent) {
		return "", errors.New("message subject does not match sender")
	}
	digest := sha256.Sum256([]byte(subject + "\x00" + id))
	return hex.EncodeToString(digest[:]), nil
}

// ValidEnvelope accepts a bounded JSON object for delivery.
func ValidEnvelope(data jsontext.Value) bool {
	return len(data) > 1 && len(data) <= 64*1024 && data.Kind() == '{' && data.IsValid()
}

// Delivery describes the daemon-held ownership of one outstanding message.
type Delivery struct {
	Group      string
	Agent      string
	Consumer   string
	Sequence   uint64
	Generation uint64
}

// Owns checks all fields that a relay acknowledgment must bind.
func Owns(delivery Delivery, req Request, consumer string, sequence, generation uint64) bool {
	return delivery.Group == req.Group && delivery.Agent == req.Agent && delivery.Consumer == consumer && delivery.Sequence == sequence && delivery.Generation == generation && sequence > 0 && generation > 0
}
