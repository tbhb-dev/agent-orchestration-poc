# Shell research gate versions and sources

Recorded 2026-09-26 for issue #30 from the `research/30-shell-conventions` worktree. Sources were cloned under `/tmp` because this sandbox cannot write to `~/Code/github.com`. The clone paths are temporary and the commits and upstream URLs below preserve the provenance. The 5.3 Bash executable was compiled in `/tmp/issue30-bash` with `./configure --prefix=/tmp/issue30-bash-install --without-bash-malloc && make -j4`; it was not installed on the host.

## Executables observed

| Tool | Version and path | Evidence |
| --- | --- | --- |
| macOS | 26.5.1, Darwin 25 | `sw_vers -productVersion`, `/bin/bash --version` |
| Apple Bash | 3.2.57(1), `/bin/bash` | `/bin/bash --version` |
| GNU Bash trial | 5.3.0(1), `/tmp/issue30-bash/bash` | Compiled from the exact source below, `--version` |
| zsh | 5.9, `/bin/zsh` | `/bin/zsh --version`, `experiments/00-system-assessment/evidence.md:650` |
| fish | Missing | `fish --version` returned command not found, `experiments/00-system-assessment/evidence.md:649` |
| ShellCheck | 0.11.0, mise pin | `mise exec -- shellcheck --version` |
| shfmt | 3.14.0, mise pin | `mise exec -- shfmt --version` |
| GNU sed | 4.10, PATH before Apple sed | `sed --version` and `command -v sed` |
| GNU coreutils | 9.11, PATH before Apple tools | `stat --version` and `command -v date stat head` |
| GNU findutils | 4.11.0, PATH before Apple tools | `xargs --version` and `command -v find xargs` |
| GNU awk | 5.4.1, PATH before Apple awk | `awk --version` and `command -v awk` |
| mise | 2026.8.6 | `mise --version` |

The host assessment's earlier shell inventory is at `experiments/00-system-assessment/evidence.md:649-656`. These are host observations, not an agent-image inventory. Bash 5.3 is a source-built trial, not the as-yet-unbuilt image interpreter.

## Versioned source checkouts

| Source | Commit read | Files used |
| --- | --- | --- |
| [GNU Bash mirror](https://github.com/mirror/bash) tag `bash-5.3` | `b8c60bc9ca365f8261fa97900b6fa939f6ebc303` at `/tmp/issue30-bash` | `CHANGES`, `doc/bashref.texi` |
| [zsh](https://github.com/zsh-users/zsh) tag `zsh-5.9` | `73d317384c9225e46d66444f93b46f0fbe7084ef` at `/tmp/issue30-zsh` | `Doc/Zsh/options.yo`, `Doc/Zsh/expn.yo` |
| [fish](https://github.com/fish-shell/fish-shell) tag `4.0.8` | `b1ec703cebf99210a98249feed92fb295bef191b` at `/tmp/issue30-fish` | `doc_src/fish_for_bash_users.rst`, `doc_src/cmds/set.rst` |
| [ShellCheck](https://github.com/koalaman/shellcheck) tag `v0.11.0` | `aac0823e6b58f8a499e856e93738082691cbf212` at `/tmp/issue30-shellcheck` | `README.md`, `shellcheck.1.md`, `CHANGELOG.md` |
| [shfmt](https://github.com/mvdan/sh) tag `v3.14.0` | `868c8e8f5cbfae87cc87d517c6aad15733fb6fc0` at `/tmp/issue30-shfmt-3.14.0` | `README.md`, `cmd/shfmt/shfmt.1.scd` |
| [GNU coreutils](https://github.com/coreutils/coreutils) tag `v9.11` | `c01fd163a47468a8296fb369f5233853bb551bb6` at `/tmp/issue30-coreutils` | `doc/coreutils.texi` date and stat options |
| [Apple shell commands](https://github.com/apple-oss-distributions/shell_cmds) source snapshot | `298787009e5432c5e4c378a077f98267077e3495` at `/tmp/issue30-apple-shell-cmds` | `date/date.1`, `find/find.1`, `xargs/xargs.1`, `basename/basename.1` |
| [Apple text commands](https://github.com/apple-oss-distributions/text_cmds) source snapshot | `592aaf8a50aa5810ee8183df20f0ba48bb23aa7e` at `/tmp/issue30-apple-text-cmds` | `sed/sed.1`, `head/head.1`, `grep/grep.1`, `tr/tr.1` |

The fish source version is documentation only because fish is absent on this host. `experiments/00-system-assessment/harness-research.md` records Claude Code 2.1.283, Codex CLI 0.157.1, and agy 1.2.10 sources and their limits. This gate reads that existing assessment instead of repeating its clones. The GNU Bash 5.3 source is unpatched release source, whereas Apple's 3.2 binary includes Apple's build choices.

The Apple source snapshots are not asserted to be the exact source build of macOS 26.5.1. Their man pages were read for the command dialect, while the installed Apple commands supplied the local runtime evidence.
