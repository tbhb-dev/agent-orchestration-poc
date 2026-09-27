// Package perms defines NATS subject permissions without broker effects.
package perms

import (
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
)

// SubjectPermissions contains allow and deny subject patterns.
type SubjectPermissions struct {
	Allow []string
	Deny  []string
}

// Permissions contains the publish and subscribe policy for one identity.
type Permissions struct {
	Publish   SubjectPermissions
	Subscribe SubjectPermissions
}

// Agent permits only attributed relay requests and lifecycle events.
func Agent(group, agent string) (Permissions, error) {
	if err := layout.ValidToken(group); err != nil {
		return Permissions{}, err
	}
	if err := layout.ValidAgent(agent); err != nil {
		return Permissions{}, err
	}
	prefix := "grp." + group
	return Permissions{
		Publish: SubjectPermissions{Allow: []string{
			prefix + ".relay.req.send." + agent,
			prefix + ".relay.req.receive." + agent,
			prefix + ".relay.req.ack." + agent,
			prefix + ".relay.req.status." + agent,
			prefix + ".relay.req.roster." + agent,
		}},
		Subscribe: SubjectPermissions{Allow: []string{
			prefix + ".relay.reply." + agent + ".>",
		}},
	}, nil
}

// Operator permits the daemon's operator to manage the group stream and inbox.
func Operator(group string) (Permissions, error) {
	if err := layout.ValidToken(group); err != nil {
		return Permissions{}, err
	}
	prefix := "grp." + group
	return Permissions{
		Publish: SubjectPermissions{Allow: []string{
			prefix + ".msg.>", prefix + ".evt.>", prefix + ".relay.reply.>", "$KV.>",
			"$JS.API.>", "$JS.ACK.>",
		}},
		Subscribe: SubjectPermissions{Allow: []string{
			prefix + ".msg.>", prefix + ".relay.req.>", prefix + ".evt.>", "_INBOX.>",
		}},
	}, nil
}
