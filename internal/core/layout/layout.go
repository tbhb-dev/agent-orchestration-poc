// Package layout defines the build bus's subject and stream values.
package layout

import (
	"fmt"
	"strings"
)

// StreamDefinition is the value translated into a JetStream stream by the bus.
type StreamDefinition struct {
	Name     string
	Subjects []string
}

// ValidToken reports whether a group or agent occupies one safe subject token.
func ValidToken(name string) error {
	if name == "" {
		return fmt.Errorf("empty name")
	}
	for i, r := range name {
		if (r >= 'a' && r <= 'z') || (i > 0 && ((r >= '0' && r <= '9') || r == '-' || r == '_')) {
			continue
		}
		return fmt.Errorf("invalid name %q", name)
	}
	return nil
}

// Broadcast returns the subject for one group's broadcast from an agent.
func Broadcast(group, from string) (string, error) {
	if err := validNames(group, from); err != nil {
		return "", err
	}
	return "grp." + group + ".msg.all." + from, nil
}

// Direct returns the subject for a message to one agent from another.
func Direct(group, to, from string) (string, error) {
	if err := validNames(group, to, from); err != nil {
		return "", err
	}
	return "grp." + group + ".msg.dm." + to + "." + from, nil
}

// Operator returns the subject for a message to the group operator.
func Operator(group, from string) (string, error) {
	if err := validNames(group, from); err != nil {
		return "", err
	}
	return "grp." + group + ".msg.op." + from, nil
}

// Event puts the sender last, so its credential can enforce attribution.
func Event(group, kind, agent string) (string, error) {
	if err := validNames(group, kind, agent); err != nil {
		return "", err
	}
	return "grp." + group + ".evt." + kind + "." + agent, nil
}

// Stream describes the one file-backed stream in each group.
func Stream(group string) (StreamDefinition, error) {
	if err := ValidToken(group); err != nil {
		return StreamDefinition{}, err
	}
	return StreamDefinition{
		Name:     "GROUP_" + strings.ToUpper(strings.ReplaceAll(group, "-", "_")),
		Subjects: []string{"grp." + group + ".msg.>", "grp." + group + ".evt.>"},
	}, nil
}

// ConsumerFilters are the broadcast and private direct subjects for an agent.
func ConsumerFilters(group, agent string) ([]string, error) {
	if err := validNames(group, agent); err != nil {
		return nil, err
	}
	return []string{"grp." + group + ".msg.all.*", "grp." + group + ".msg.dm." + agent + ".*"}, nil
}

func validNames(names ...string) error {
	for _, name := range names {
		if err := ValidToken(name); err != nil {
			return err
		}
	}
	return nil
}
