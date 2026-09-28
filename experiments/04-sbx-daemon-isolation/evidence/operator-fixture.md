# Unexecuted operator fixture proposal

These commands are a proposal for an operator-authorized disposable macOS account. They have not run. The operator must first confirm that this host supports an independent login context for `sbx` and that the new account can access the installed binary without inheriting the operator's Keychain, daemon, state, or trust inputs. Capture the operator's process, socket, settings, sandbox, and trust inventory before and after without printing any secret value. Stop immediately if a path or process resolves to UID 501 or `/Users/tony`.

## Create and establish the target

Run as the operator, with interactive password prompts and no password on the command line:

```sh
sudo sysadminctl -addUser sbx-bv05-237 -fullName 'Disposable BV05 sbx' -home /Users/sbx-bv05-237 -password -
sudo -iu sbx-bv05-237 /usr/bin/id
sudo -iu sbx-bv05-237 /usr/bin/printenv HOME
```

**Changes:** creates one non-admin macOS account and home. **Undo:** after the fixture has stopped and inventory proves no daemon or VM remains, run `sudo sysadminctl -deleteUser sbx-bv05-237 -secure`. Record the assigned UID before deletion. A login Keychain or state outside the home is residue until the operator verifies its removal.

The separate user's expected state root is `/Users/sbx-bv05-237/Library/Application Support/com.docker.sandboxes/`. Its expected credential binding file is `/Users/sbx-bv05-237/.config/sbx/credentials.yaml`. Its expected conditional audit path is `/Users/sbx-bv05-237/Library/Logs/com.docker.sandboxes/sandboxes/auditkit/`. These paths derive from pinned docs and the proposed home, not an observed run. Record the actual daemon socket, settings override file, VM files, temporary sockets, and Keychain scope before proceeding.

## Stateful fixture after authorization

Run these commands only after the operator confirms the account boundary. `sudo -i` requests the target user's login environment. Record the effective UID, home, parent process, daemon PID, socket, and before inventory before the first command. `sbx settings get` is included only inside the disposable account because it may start a daemon.

```sh
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx daemon start --detach
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx settings get --json kit.allowLocalKits
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx settings set kit.allowLocalKits false
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx settings get --json kit.allowLocalKits
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx create --name bv05-clean shell
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx rm bv05-clean
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx settings unset kit.allowLocalKits
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx daemon stop
```

**Changes:** starts a daemon and writes one setting override, then creates a mountless sandbox. **Undo:** the `sbx rm`, `settings unset`, and `daemon stop` commands above reverse the individual changes. Do not substitute `sbx reset`, since its scope includes every sandbox, secret, and sign-in visible to that account. Verify each command's exit status and record before, during, and after inventories under both UIDs.

The `false` value tests a disposable setting change. A later local-kit probe in #229 may require `true` in this same verified target. That later probe is outside this experiment.

## Conditional process trust check

The prior BV-05 [proposal](../../03-sbx-kit-trust/evidence/read-only.md) names `SSL_CERT_FILE` as a process-scoped host-bundle candidate, although its effect on the v0.45.1 daemon is unverified. If the operator authorizes a targeted check and a public-only `/Users/sbx-bv05-237/bv05-host-bundle.pem` exists, start a second disposable daemon with this exact input after the first daemon has stopped:

```sh
sudo -iu sbx-bv05-237 /usr/bin/env SSL_CERT_FILE=/Users/sbx-bv05-237/bv05-host-bundle.pem /opt/homebrew/bin/sbx daemon start --detach
sudo -iu sbx-bv05-237 /opt/homebrew/bin/sbx daemon stop
sudo -iu sbx-bv05-237 /bin/rm /Users/sbx-bv05-237/bv05-host-bundle.pem
```

**Changes:** supplies one public trust file path to the new daemon process and deletes that file after stopping it. **Undo:** stop the disposable daemon and remove the public-only file. Verify actual trust behavior with a controlled TLS endpoint before calling this mechanism supported. Keep macOS system trust unchanged.

## Final cleanup proof

After the daemon and sandbox are gone, record the disposable UID's state, binding, audit, socket, temporary paths, Keychain items, and running processes. Ask the operator to remove any confirmed disposable residue outside the home by exact observed path. Then run:

```sh
sudo sysadminctl -deleteUser sbx-bv05-237 -secure
```

Compare the operator's before and after state-root, settings, daemon, sandbox, socket, and trust inventories. Compare content digests where permitted because timestamps alone show only metadata. Do not read or commit secret values. List any remaining path or process and its cleanup command before declaring isolation verified.
