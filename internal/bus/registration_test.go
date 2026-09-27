package bus

import (
	"net"
	"os"
	"testing"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

func TestRegisterAgent(t *testing.T) {
	ctx := t.Context()
	cfg := Config{StateDir: t.TempDir(), Port: -1, Groups: []Group{{Name: "build", Agents: []string{"claude"}}}}
	b, err := Start(ctx, cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer b.Close()
	cfg.Groups[0].Agents = []string{"claude", "codex"}
	cfg.Port = b.server.Addr().(*net.TCPAddr).Port
	if err := b.RegisterAgent(ctx, cfg, "build", "codex"); err != nil {
		t.Fatal(err)
	}
	path, err := b.CredentialPath("build", "codex")
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil || info.Mode().Perm() != 0o600 {
		t.Fatalf("credential file = %v, %v", info, err)
	}
	client := connectAgent(t, b, "codex")
	client.Close()
	oldClient := connectAgent(t, b, "claude")
	oldClient.Close()
	operator := connectAgent(t, b, "operator")
	defer operator.Close()
	js, err := jetstream.New(operator)
	if err != nil {
		t.Fatal(err)
	}
	stream, err := js.Stream(ctx, "GROUP_BUILD")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := stream.Consumer(ctx, "codex"); err != nil {
		t.Fatal(err)
	}
}

func connectAgent(t *testing.T, b *Bus, name string) *nats.Conn {
	t.Helper()
	path, err := b.CredentialPath("build", name)
	if err != nil {
		t.Fatal(err)
	}
	option, err := nats.NkeyOptionFromSeed(path)
	if err != nil {
		t.Fatal(err)
	}
	conn, err := nats.Connect(b.URL(), option)
	if err != nil {
		t.Fatal(err)
	}
	return conn
}
