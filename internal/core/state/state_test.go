package state

import (
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func TestStatus(t *testing.T) {
	for _, tc := range []struct {
		name  string
		value Status
		valid bool
	}{
		{"working", Status{State: "working", UpdatedAt: "now"}, true},
		{"idle", Status{State: "idle", Detail: "done", UpdatedAt: "now"}, true},
		{"blocked", Status{State: "blocked", UpdatedAt: "now"}, true},
		{"bad state", Status{State: "away", UpdatedAt: "now"}, false},
		{"missing time", Status{State: "idle"}, false},
		{"large", Status{State: "idle", Detail: strings.Repeat("x", MaxValueBytes), UpdatedAt: "now"}, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			data, err := EncodeStatus(tc.value)
			if (err == nil) != tc.valid {
				t.Fatalf("EncodeStatus = %v", err)
			}
			if tc.valid {
				got, err := DecodeStatus(data)
				if err != nil || got != tc.value {
					t.Fatalf("DecodeStatus = %#v, %v", got, err)
				}
			}
		})
	}
	if _, err := DecodeStatus([]byte("{")); err == nil {
		t.Fatal("accepted invalid JSON")
	}
}

func TestRoster(t *testing.T) {
	for _, tc := range []struct {
		value Roster
		valid bool
	}{
		{Roster{Role: "worker", JoinedAt: "now"}, true},
		{Roster{Role: "", JoinedAt: "now"}, false},
		{Roster{Role: "worker"}, false},
	} {
		data, err := EncodeRoster(tc.value)
		if (err == nil) != tc.valid {
			t.Fatalf("EncodeRoster = %v", err)
		}
		if tc.valid {
			got, err := DecodeRoster(data)
			if err != nil || got != tc.value {
				t.Fatalf("DecodeRoster = %#v, %v", got, err)
			}
		}
	}
	if _, err := DecodeRoster([]byte(strings.Repeat("x", MaxValueBytes+1))); err == nil {
		t.Fatal("accepted oversized roster")
	}
}

func TestStateRoundTripProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		detail := rapid.StringMatching(`[a-zA-Z0-9 ]{0,100}`).Draw(t, "detail")
		status := Status{State: "working", Detail: detail, UpdatedAt: "now"}
		data, err := EncodeStatus(status)
		if err != nil {
			t.Fatal(err)
		}
		got, err := DecodeStatus(data)
		if err != nil || got != status {
			t.Fatalf("status = %#v, %v", got, err)
		}
	})
}
