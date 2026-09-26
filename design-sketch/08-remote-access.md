# Remote access

The operator wants the web UI reachable from other devices without exposing the daemon to the public internet. Tailscale is the chosen mechanism. The design conversation first considered Cloudflare Tunnel with Access; that's out of scope now but the policy thinking carries over.

## Candidate integrations

The best option should be chosen by experiment.

| Option | How it works | For | Against |
| --- | --- | --- | --- |
| `tsnet` embedded in the daemon | The daemon joins the tailnet as its own node and listens on it | No separate process; the daemon can ask Tailscale who each caller is and apply per-user policy; HTTPS certificates through Tailscale | Only direct if the daemon is Go; the node needs its own auth and state |
| `tailscale serve` in front of a loopback daemon | The system Tailscale proxies a tailnet HTTPS URL to `127.0.0.1` | No code in the daemon; uses the machine's existing Tailscale | Identity comes through headers set by `serve` (to be confirmed), which the daemon must only trust from the local proxy |
| Plain tailnet bind | The daemon binds the Mac's tailnet address | Simplest | No HTTPS without extra work; identity requires a separate lookup |

Tailscale Funnel (public exposure) stays off.

## Policy

- The daemon trusts only loopback clients (the Tauri app, with a per-launch token) and tailnet clients whose Tailscale identity is on an allowlist in settings.
- Remote clients can view, type into, message, stop, and restart sessions, and create groups only against allowlisted repository roots. Remote clients can never set mount paths.
- Remote operator shells are off by default. When enabled, opening a shell remotely should require something stronger than an existing session, such as re-confirmation from the Tauri app or a short-lived approval.
- No host shells over the remote path, only VM shells.
- WebSocket keepalives every 30 seconds or so, with reconnect and snapshot restore in the client, since mobile networks drop connections.

## Experiments

- `tsnet` versus `tailscale serve` with the daemon (in whichever language wins), including how each exposes caller identity.
- Keystroke echo latency locally and over the tailnet from a phone.
- Certificate handling for the tailnet hostname.
