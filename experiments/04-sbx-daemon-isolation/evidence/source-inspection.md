# Pinned source and documentation inspection

All six documentation reads used `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` and exited 0. For each row, the exact command was `gh api 'repos/dvdksn/docs/contents/<path>?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '<range>' > experiments/04-sbx-daemon-isolation/evidence/pinned-<name>-excerpt.txt`, with `<path>`, `<range>`, and `<name>` as shown. The command ran in zsh with `set -o pipefail`.

The captured excerpts had whitespace on blank numbered lines removed with `sed -i 's/[[:space:]]*$//' experiments/04-sbx-daemon-isolation/evidence/pinned-*-excerpt.txt` for the Git whitespace check. Text on nonblank lines is unchanged.

The expanded commands were:

```sh
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/architecture.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '44,55p;119,127p' > experiments/04-sbx-daemon-isolation/evidence/pinned-architecture-excerpt.txt
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/troubleshooting.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '423,479p' > experiments/04-sbx-daemon-isolation/evidence/pinned-troubleshooting-excerpt.txt
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/configuration/credentials.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '47,79p;430,449p' > experiments/04-sbx-daemon-isolation/evidence/pinned-credentials-excerpt.txt
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/governance/audit/local.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '64,81p' > experiments/04-sbx-daemon-isolation/evidence/pinned-audit-excerpt.txt
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/configuration/upstream-proxy.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '75,99p' > experiments/04-sbx-daemon-isolation/evidence/pinned-upstream-proxy-excerpt.txt
gh api 'repos/dvdksn/docs/contents/content/manuals/ai/sandboxes/install.md?ref=75d1ee312280c2028be294e043edeaf35f2fe1bb' --jq .content | base64 -d | nl -ba | sed -n '60,67p' > experiments/04-sbx-daemon-isolation/evidence/pinned-install-excerpt.txt
```

| Name | Path under repository root | Range | Relevant evidence |
| --- | --- | --- | --- |
| architecture | `content/manuals/ai/sandboxes/architecture.md` | `44,55p;119,127p` | Sandbox persistence and `sbx rm` |
| troubleshooting | `content/manuals/ai/sandboxes/troubleshooting.md` | `423,479p` | macOS state root and reset behavior |
| credentials | `content/manuals/ai/sandboxes/configuration/credentials.md` | `47,79p;430,449p` | macOS Keychain and separate binding file |
| audit | `content/manuals/ai/sandboxes/governance/audit/local.md` | `64,81p` | Conditional macOS audit path |
| upstream-proxy | `content/manuals/ai/sandboxes/configuration/upstream-proxy.md` | `75,99p` | Environment and settings precedence for proxy traffic |
| install | `content/manuals/ai/sandboxes/install.md` | `60,67p` | macOS Homebrew installation |

The exact local source checks were `gh api repos/docker/sbx --jq '{full_name, private, default_branch}'` (HTTP 404), `gh api repos/docker/sbx-releases/releases/tags/v0.45.1 --jq '{tag_name, target_commitish, published_at, body}'` (exit 0), and `realpath /opt/homebrew/bin/sbx` (exit 0). macOS selector, socket, settings, and Keychain behavior remain unverified from source.
