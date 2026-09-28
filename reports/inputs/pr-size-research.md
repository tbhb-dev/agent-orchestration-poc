# Pull request size research for issue #84

## Version and source

Documented: `scc` v4.1.0 is pinned in the `scc:version` mise task. Its tagged source was cloned to `/tmp/scc-84-source` at commit `c651b07a7d3aa6e97a476380eef0f478a53719a3`. I read `README.md` lines 210–255 and 1035–1075, `config.go` around the generated-marker defaults, and `processor/workers.go` around minified and generated detection. The upstream [release](https://github.com/boyter/scc/releases/tag/v4.1.0) identifies this version.

Documented: `scc --by-file --format json --gen --min --no-config --no-cocomo --no-complexity` reports file classifications while retaining detected generated and minified files. The source describes a default average line length of 255 bytes for minification and generated markers including `do not edit`. The tool's own default excludes some lockfiles, so the contract must retain git raw counts independently for every file.

Observed: `mise exec -- scc --version` exited 1 because the sandbox denied creation of `~/.local/share/mise/installs/go-github-com-boyter-scc-v4/4.1.0`. The task-scoped pin leaves ordinary checks runnable. No alternate install directory or tool was used.

## Diff-to-count comparison

The first candidate classifies each added and removed fragment in its original file context with `scc`, then sums the `Code` counts from each fragment. It counts a replacement as added plus deleted work, and a balanced edit cannot disappear. It requires a way to preserve enough context for multiline comments and language detection.

The second candidate runs `scc` over the base and head file and takes the absolute difference of their `Code` counts. It loses balanced edits. For example, replacing one code statement with another yields one changed line by the first method on each side but zero by the second method. It also loses deletions when an equal number of code lines are added.

Inference: fragment classification is the closer match for the issue's added-plus-deleted unit, but a fragment inside a multiline comment can be misclassified without surrounding state. The counter must either pass recorded context to classification or mark the file for review when context cannot be reproduced. Code moved without a net line change still counts on both sides. The pure decision stage takes recorded raw diff lines and recorded classifier results, then applies exclusion reasons. Collection of git blobs and `scc` output belongs in the shell.

Untested: the exact `scc` JSON shape, fragment behavior, rename and deletion handling, and fixture outputs remain for the dependent counter item because the pinned binary could not install in this sandbox. The fixture command `mise run check:pr-size-contract` is deferred with that item. Issue #93 owns CI enforcement after the counter exists.
