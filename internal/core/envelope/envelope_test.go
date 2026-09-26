package envelope

import (
	"reflect"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

func testMessage(text string) Message {
	return Message{Body: Body{Text: text, Refs: map[string]int{"issue": 27}}, Headers: Headers{
		ID: "message-1", Kind: "message", Timestamp: "2026-09-26T00:00:00Z",
	}}
}

func TestEncodeDecode(t *testing.T) {
	for _, tc := range []struct {
		name    string
		message Message
		valid   bool
	}{
		{"message", testMessage("hello"), true},
		{"empty text", testMessage(""), false},
		{"long text", testMessage(strings.Repeat("a", MaxTextBytes+1)), false},
		{"bad ID", func() Message { m := testMessage("hello"); m.Headers.ID = "x\ny"; return m }(), false},
		{"empty ID", func() Message { m := testMessage("hello"); m.Headers.ID = ""; return m }(), false},
		{"bad kind", func() Message { m := testMessage("hello"); m.Headers.Kind = "bad"; return m }(), false},
		{"bad ref", func() Message { m := testMessage("hello"); m.Body.Refs["issue"] = -1; return m }(), false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			body, headers, err := Encode(tc.message)
			if (err == nil) != tc.valid {
				t.Fatalf("Encode error = %v", err)
			}
			if !tc.valid {
				return
			}
			decoded, err := Decode(body, headers)
			if err != nil || !reflect.DeepEqual(decoded, tc.message) {
				t.Fatalf("Decode = %#v, %v", decoded, err)
			}
		})
	}
}

func TestDecodeRejectsInvalid(t *testing.T) {
	for _, body := range [][]byte{[]byte("{"), []byte(`{"text":""}`), []byte(strings.Repeat("x", MaxBodyBytes+1))} {
		if _, err := Decode(body, map[string]string{"Nats-Msg-Id": "id", "Kind": "message", "Timestamp": "now"}); err == nil {
			t.Fatalf("accepted %q", body[:min(len(body), 20)])
		}
	}
}

func TestRoundTripProperty(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		text := rapid.StringMatching(`[a-zA-Z0-9 ]{1,100}`).Draw(t, "text")
		message := testMessage(text)
		message.Headers.CorrelationID = rapid.StringMatching(`[a-z0-9]{0,20}`).Draw(t, "correlation")
		body, headers, err := Encode(message)
		if err != nil {
			t.Fatal(err)
		}
		got, err := Decode(body, headers)
		if err != nil || !reflect.DeepEqual(got, message) {
			t.Fatalf("round trip = %#v, %v", got, err)
		}
	})
}

func TestIsReplyTo(t *testing.T) {
	answer := testMessage("done")
	answer.Headers.Kind = "answer"
	answer.Headers.CorrelationID = "question-1"
	if !IsReplyTo(answer, "question-1") || IsReplyTo(answer, "question-2") || IsReplyTo(answer, "") {
		t.Fatal("incorrect answer correlation")
	}
	answer.Headers.Kind = "question"
	if IsReplyTo(answer, "question-1") {
		t.Fatal("accepted question as reply")
	}
}
