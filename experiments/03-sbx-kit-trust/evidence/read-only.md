# Read-only evidence, 2026-09-28

All commands below ran in `exp/229-sbx-kit-trust` on macOS 26.5.1 arm64. No sbx daemon, settings, secret, sandbox, kit installation, receiver, or trust-store operation was invoked. The existing daemon state and effective settings were not read because `sbx settings --help` says settings reads can start the daemon.

| Command | Exit | Selected output |
| --- | --- | --- |
| `sbx --version` | 1 | `error: unknown flag: --version` |
| `sbx version` | 0 | `sbx version: v0.45.1 9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` |
| `sbx create --help` | 0 | `sbx create [flags] AGENT\|SANDBOX_KIT [PATH...]`, `--kit strings`, `--name string`, `-q` |
| `sbx kit validate --help` | 0 | `sbx kit validate REFERENCE [flags]` |
| `sbx settings --help` | 0 | Settings commands use the local daemon and start it if necessary |
| `sbx settings set --help` | 0 | Overrides a setting, with environment variables taking precedence |
| `sbx daemon start --help` | 0 | No isolated config or state directory flag advertised |
| `sw_vers` | 0 | macOS 26.5.1, build 25F80 |
| `uname -m` | 0 | `arm64` |

**Documented:** the pinned kit reference at `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` separates `credentials[].apiKey.inject` from `permissions.network.allow`. It rejects v1 fields and maps `files/home/` before `setup.install`. Pinned credentials documentation says third-party v2 kits require a credential binding. Pinned host-services documentation says the guest uses `host.docker.internal` while the proxy translates to `localhost`, and the policy allowlist uses `localhost:<port>`. Pinned troubleshooting says the `forward` proxy presents its own guest-trusted certificate and warns against replacing the guest trust bundle.

**Help-text:** `sbx settings --help` advertises daemon startup on a settings read. `sbx kit validate --help` does not establish whether validation has daemon side effects. The inspected help output leaves isolated daemon/configuration selection unproven.

**Inference:** a guest CA installation alone cannot be assumed to configure the host proxy's upstream trust. The proxy uses a separate TLS connection according to the imported authentication design. The first live negative control must identify the failing hop before a process-scoped host bundle is considered.

## Required case status

| Case | Expected observation | Actual evidence | Classification |
| --- | --- | --- | --- |
| 1. Local kits and binding | Headless creation, disabled-setting rejection, binding enforcement, idempotent setup | Only CLI and documentation support for these controls | Blocked by operator state-change gate |
| 2. CA and leaf matrix | Receiver TLS/SNI and injection for valid leaf, rejection for other CA, wrong name, and expiry | No receiver or sandbox started | Blocked by operator state-change gate |
| 3. Host route | Guest URL, DNS/dial, policy target, injection match, and upstream verification name recorded separately | `host.docker.internal` to `localhost` is documented, runtime matching is untested | Blocked by operator state-change gate |
| 4. Trust and restart | Public-only kit, preserved proxy trust, leaf renewal and restart without a new root | Trust-store warning is documented, no kit or restart run | Blocked by operator state-change gate |
| 5. Optional client certificate | Receiver requests optional client certificate while proxy injects bearer value | No receiver or proxy request run | Blocked by operator state-change gate |
| 6. Bounded wait | Hold duration, timeout/reconnection traces, unchanged delivery evidence | This branch lacks a fixture for sbx transport and delivery | Unsupported in this partial fixture |

Property acceptance remains open for every case, and all Docker Sandboxes harness matrix cells are untested. The fixture did not use an interim operator control path. The provisional exact-path binding and single-incarnation wrapper were not used or tested. The reviewer additions remain proposed and untested.
