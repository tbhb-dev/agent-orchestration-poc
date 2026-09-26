// Package version holds the build version stamped into the binaries.
package version

// Version is the build version. The build task overrides it with
// -ldflags "-X github.com/tbhb/agent-orchestration-poc/internal/version.Version=...".
var Version = "dev"

// String returns the version the binary was built with.
func String() string {
	return Version
}
