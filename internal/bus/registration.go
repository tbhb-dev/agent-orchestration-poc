package bus

import (
	"context"
	"path/filepath"

	"github.com/nats-io/nats-server/v2/server"
)

// RegisterAgent reloads the complete group roster and creates the new inbox.
// The caller supplies the full roster, including the new agent.
func (b *Bus) RegisterAgent(ctx context.Context, cfg Config, groupName, agentName string) error {
	opts := &server.Options{
		Host: "127.0.0.1", Port: cfg.Port, JetStream: true,
		StoreDir: filepath.Join(cfg.StateDir, "store"), NoLog: true, NoSigs: true,
	}
	for _, group := range cfg.Groups {
		account, _, err := configureGroup(cfg.StateDir, group, opts)
		if err != nil {
			return err
		}
		opts.Accounts = append(opts.Accounts, account)
	}
	if err := b.server.ReloadOptions(opts); err != nil {
		return err
	}
	return b.createStream(ctx, Group{Name: groupName, Agents: []string{agentName}}, filepath.Join(cfg.StateDir, "credentials", groupName, "operator.seed"))
}
