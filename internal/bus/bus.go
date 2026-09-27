// Package bus hosts the embedded NATS server and translates core values into broker configuration.
package bus

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/nats-io/nats-server/v2/server"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"github.com/nats-io/nkeys"
	"github.com/tbhb/agent-orchestration-poc/internal/core/layout"
	"github.com/tbhb/agent-orchestration-poc/internal/core/perms"
)

// Group names an account and its initial agents.
type Group struct {
	Name   string
	Agents []string
}

// Config provides the storage directory, listener port, and initial groups.
type Config struct {
	StateDir string
	Port     int
	Groups   []Group
}

// Bus owns the server until Close is called.
type Bus struct {
	server *server.Server
	state  string
}

// Start creates credentials, starts JetStream, and provisions the group streams.
func Start(ctx context.Context, cfg Config) (_ *Bus, err error) {
	if cfg.StateDir == "" || len(cfg.Groups) == 0 {
		return nil, errors.New("state directory and at least one group are required")
	}
	if err := os.MkdirAll(cfg.StateDir, 0o700); err != nil {
		return nil, err
	}
	opts := &server.Options{
		Host: "127.0.0.1", Port: cfg.Port, JetStream: true,
		StoreDir: filepath.Join(cfg.StateDir, "store"), NoLog: true, NoSigs: true,
	}
	operators := make(map[string]string, len(cfg.Groups))
	for _, group := range cfg.Groups {
		account, operator, err := configureGroup(cfg.StateDir, group, opts)
		if err != nil {
			return nil, err
		}
		opts.Accounts = append(opts.Accounts, account)
		operators[group.Name] = operator
	}
	srv, err := server.NewServer(opts)
	if err != nil {
		return nil, err
	}
	bus := &Bus{server: srv, state: cfg.StateDir}
	defer func() {
		if err != nil {
			bus.Close()
		}
	}()
	srv.Start()
	if !srv.ReadyForConnections(10 * time.Second) {
		return nil, errors.New("NATS server did not become ready")
	}
	for _, group := range cfg.Groups {
		if err := bus.createStream(ctx, group, operators[group.Name]); err != nil {
			return nil, err
		}
	}
	return bus, nil
}

func configureGroup(state string, group Group, opts *server.Options) (*server.Account, string, error) {
	if err := layout.ValidToken(group.Name); err != nil {
		return nil, "", err
	}
	account := server.NewAccount(group.Name)
	operator, err := addCredential(state, group.Name, "operator", account, opts, perms.Operator)
	if err != nil {
		return nil, "", err
	}
	for _, agent := range group.Agents {
		if err := layout.ValidAgent(agent); err != nil {
			return nil, "", err
		}
		if _, err := addCredential(state, group.Name, agent, account, opts, func(group string) (perms.Permissions, error) {
			return perms.Agent(group, agent)
		}); err != nil {
			return nil, "", err
		}
	}
	return account, operator, nil
}

func addCredential(state, group, agent string, account *server.Account, opts *server.Options, policy func(string) (perms.Permissions, error)) (string, error) {
	if err := layout.ValidToken(agent); err != nil {
		return "", err
	}
	p, err := policy(group)
	if err != nil {
		return "", err
	}
	path := filepath.Join(state, "credentials", group, agent+".seed")
	public, err := credential(path)
	if err != nil {
		return "", err
	}
	opts.Nkeys = append(opts.Nkeys, &server.NkeyUser{
		Nkey: public, Account: account,
		Permissions: &server.Permissions{
			Publish:   &server.SubjectPermission{Allow: p.Publish.Allow, Deny: p.Publish.Deny},
			Subscribe: &server.SubjectPermission{Allow: p.Subscribe.Allow, Deny: p.Subscribe.Deny},
		},
	})
	return path, nil
}

func credential(path string) (string, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return "", err
	}
	seed, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		seed, err = createCredential(path)
	}
	defer clear(seed)
	if err != nil {
		return "", err
	}
	info, err := os.Stat(path)
	if err != nil {
		return "", err
	}
	if info.Mode().Perm() != 0o600 {
		return "", fmt.Errorf("credential %s must have mode 0600", path)
	}
	pair, err := nkeys.FromSeed(seed)
	if err != nil {
		return "", err
	}
	defer pair.Wipe()
	return pair.PublicKey()
}

func createCredential(path string) ([]byte, error) {
	pair, err := nkeys.CreateUser()
	if err != nil {
		return nil, err
	}
	defer pair.Wipe()
	seed, err := pair.Seed()
	defer clear(seed)
	if err != nil {
		return nil, err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return nil, err
	}
	_, writeErr := file.Write(seed)
	closeErr := file.Close()
	if err := errors.Join(writeErr, closeErr); err != nil {
		return nil, err
	}
	return append([]byte(nil), seed...), nil
}

func (b *Bus) createStream(ctx context.Context, group Group, operatorPath string) error {
	account, err := b.server.LookupAccount(group.Name)
	if err != nil {
		return err
	}
	if err := account.EnableJetStream(nil, nil); err != nil {
		return err
	}
	option, err := nats.NkeyOptionFromSeed(operatorPath)
	if err != nil {
		return err
	}
	conn, err := nats.Connect(b.server.ClientURL(), option)
	if err != nil {
		return err
	}
	defer conn.Close()
	js, err := jetstream.New(conn)
	if err != nil {
		return err
	}
	definition, err := layout.Stream(group.Name)
	if err != nil {
		return err
	}
	stream, err := js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{
		Name: definition.Name, Subjects: definition.Subjects,
		Storage: streamStorage(definition.Storage), Retention: streamRetention(definition.Retention),
		NoAck: definition.NoAck,
	})
	if err != nil {
		return err
	}
	for _, agent := range group.Agents {
		definition, err := layout.Consumer(group.Name, agent)
		if err != nil {
			return err
		}
		_, err = stream.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
			Name: definition.Name, Durable: definition.Name,
			FilterSubjects: definition.FilterSubjects, AckPolicy: consumerAck(definition.AckPolicy),
		})
		if err != nil {
			return err
		}
	}
	return nil
}

func streamStorage(value string) jetstream.StorageType {
	return map[string]jetstream.StorageType{"file": jetstream.FileStorage}[value]
}

func streamRetention(value string) jetstream.RetentionPolicy {
	return map[string]jetstream.RetentionPolicy{"limits": jetstream.LimitsPolicy}[value]
}

func consumerAck(value string) jetstream.AckPolicy {
	return map[string]jetstream.AckPolicy{"explicit": jetstream.AckExplicitPolicy}[value]
}

// URL is the IPv4 loopback address that clients use.
func (b *Bus) URL() string { return b.server.ClientURL() }

// CredentialPath names a credential file without exposing its seed.
func (b *Bus) CredentialPath(group, agent string) (string, error) {
	if err := layout.ValidToken(group); err != nil {
		return "", err
	}
	if err := layout.ValidToken(agent); err != nil {
		return "", err
	}
	return filepath.Join(b.state, "credentials", group, agent+".seed"), nil
}

// Close stops the embedded server.
func (b *Bus) Close() {
	if b != nil && b.server != nil {
		b.server.Shutdown()
		b.server.WaitForShutdown()
	}
}
