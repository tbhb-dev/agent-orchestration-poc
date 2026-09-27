package bus

import (
	"net"
	"os"
	"testing"

	"github.com/nats-io/nats.go"
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
	url := b.URL()
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
	option, err := nats.NkeyOptionFromSeed(path)
	if err != nil {
		t.Fatal(err)
	}
	client, err := nats.Connect(url, option)
	if err != nil {
		t.Fatal(err)
	}
	client.Close()
	oldPath, err := b.CredentialPath("build", "claude")
	if err != nil {
		t.Fatal(err)
	}
	oldOption, err := nats.NkeyOptionFromSeed(oldPath)
	if err != nil {
		t.Fatal(err)
	}
	oldClient, err := nats.Connect(url, oldOption)
	if err != nil {
		t.Fatalf("existing agent lost access after reload: %v", err)
	}
	oldClient.Close()
}
