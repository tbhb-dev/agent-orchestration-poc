package subject_test

import (
	"strings"
	"testing"

	"github.com/tbhb/agent-orchestration-poc/internal/core/subject"
	"pgregory.net/rapid"
)

func TestValid(t *testing.T) {
	cases := []struct {
		name  string
		valid bool
	}{
		{"a", true},
		{"a.b-2_c", true},
		{strings.Repeat("a", 255), true},
		{"", false},
		{".a", false},
		{"a.", false},
		{"a..b", false},
		{"a.*", false},
		{"a.>", false},
		{"a.B", false},
		{"a/b", false},
		{"é", false},
		{strings.Repeat("a", 256), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := subject.Valid(tc.name)
			if (err == nil) != tc.valid {
				t.Fatalf("Valid(%q) = %v, want valid=%t", tc.name, err, tc.valid)
			}
		})
	}
}

func TestValidProperties(t *testing.T) {
	token := rapid.StringMatching(`[a-z0-9_-]{1,12}`)
	t.Run("joined plain tokens are valid", rapid.MakeCheck(func(t *rapid.T) {
		tokens := rapid.SliceOfN(token, 1, 6).Draw(t, "tokens")
		name := strings.Join(tokens, ".")
		if err := subject.Valid(name); err != nil {
			t.Fatalf("Valid(%q) = %v", name, err)
		}
	}))
	t.Run("an empty token is invalid", rapid.MakeCheck(func(t *rapid.T) {
		left := token.Draw(t, "left")
		right := token.Draw(t, "right")
		name := left + ".." + right
		if err := subject.Valid(name); err == nil {
			t.Fatalf("Valid(%q) = nil", name)
		}
	}))
}
