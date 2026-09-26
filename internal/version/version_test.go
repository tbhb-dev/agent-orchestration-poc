package version

import "testing"

func TestString(t *testing.T) {
	tests := []struct {
		name    string
		version string
		want    string
	}{
		{name: "default", version: "dev", want: "dev"},
		{name: "tag", version: "v0.1.0", want: "v0.1.0"},
		{name: "commit", version: "8b06815", want: "8b06815"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			previous := Version
			t.Cleanup(func() { Version = previous })
			Version = tt.version
			if got := String(); got != tt.want {
				t.Errorf("String() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestDefaultIsDev(t *testing.T) {
	if Version != "dev" {
		t.Errorf("Version = %q, want %q", Version, "dev")
	}
}
