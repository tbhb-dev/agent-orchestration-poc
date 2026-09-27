// Package client carries agentctl requests through the authenticated daemon relay.
package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json/v2"
	"fmt"
	"net"
	"strconv"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/tbhb/agent-orchestration-poc/internal/core/agentctl"
	"github.com/tbhb/agent-orchestration-poc/internal/core/relay"
)

// Client owns one agent connection and uses no JetStream API grant.
type Client struct{ conn *nats.Conn }

// Connect reads the credential from its file and connects to loopback.
func Connect(cmd agentctl.Command) (*Client, error) {
	option, err := nats.NkeyOptionFromSeed(cmd.CredsFile)
	if err != nil {
		return nil, fmt.Errorf("read credential file: %w", err)
	}
	address := net.JoinHostPort("127.0.0.1", strconv.Itoa(cmd.Port))
	conn, err := nats.Connect("nats://"+address, option, nats.Timeout(3*time.Second))
	if err != nil {
		return nil, fmt.Errorf("connect to bus: %w", err)
	}
	return &Client{conn: conn}, nil
}

// Close releases the connection.
func (client *Client) Close() { client.conn.Close() }

// NewID returns a random lowercase token usable as a relay or message ID.
func NewID() (string, error) {
	var bytes [16]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		return "", err
	}
	return "r" + hex.EncodeToString(bytes[:]), nil
}

// Call sends one operation and waits on its exact authenticated reply subject.
func (client *Client) Call(cmd agentctl.Command, request agentctl.Request) (agentctl.Response, error) {
	identity := relay.Request{Group: cmd.Group, Agent: cmd.Agent, Operation: cmd.Name}
	reply, err := relay.Reply(identity, request.ID)
	if err != nil {
		return agentctl.Response{}, err
	}
	sub, err := client.conn.SubscribeSync(reply)
	if err != nil {
		return agentctl.Response{}, err
	}
	defer func() { _ = sub.Unsubscribe() }()
	if err := client.conn.Flush(); err != nil {
		return agentctl.Response{}, err
	}
	data, err := json.Marshal(request)
	if err != nil {
		return agentctl.Response{}, err
	}
	subject := "grp." + cmd.Group + ".relay.req." + cmd.Name + "." + cmd.Agent
	if err := client.conn.Publish(subject, data); err != nil {
		return agentctl.Response{}, err
	}
	message, err := sub.NextMsg(time.Duration(request.TimeoutMS)*time.Millisecond + 7*time.Second)
	if err != nil {
		return agentctl.Response{}, err
	}
	var response agentctl.Response
	if err := json.Unmarshal(message.Data, &response); err != nil {
		return agentctl.Response{}, err
	}
	return response, nil
}
