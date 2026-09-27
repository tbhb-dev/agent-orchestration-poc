// Package subject validates bus subject names.
package subject

import (
	"errors"
	"strings"
)

// Valid reports whether name is a plain bus subject of at most 255 bytes.
func Valid(name string) error {
	if name == "" || len(name) > 255 {
		return errors.New("subject name must contain 1 to 255 bytes")
	}
	for _, token := range strings.Split(name, ".") {
		if token == "" {
			return errors.New("subject name has an empty token")
		}
		for _, char := range token {
			if (char < 'a' || char > 'z') && (char < '0' || char > '9') && char != '-' && char != '_' {
				return errors.New("subject name has an invalid character")
			}
		}
	}
	return nil
}
