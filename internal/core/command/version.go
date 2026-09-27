// Package command decides the response to a version command.
package command

// Version returns the message and exit code for a version-only command.
func Version(args []string, name, version, usage string) (string, int) {
	if len(args) == 1 && args[0] == "version" {
		return name + " " + version, 0
	}
	return usage, 2
}
