# Failing gate examples, 2026-09-26

Each probe was a throwaway file in this worktree. Each command ran through mise with the pinned configuration. Cache warnings from the sandboxed Go user cache and trailing whitespace are omitted from the displayed output. The probe files were removed after each run.

## Depguard

Command: `mise run check:go`. Exit status: 1. Probe: internal/core/boundary_probe.go.

```text
[check:go] $ scripts/check-gofumpt.sh
[check:go] $ go vet ./...
[check:go] $ go mod tidy -diff
[check:go] $ go mod verify
all modules verified
[check:go] $ golangci-lint run ./...
internal/core/boundary_probe.go:3:8: import 'os' is not allowed from list 'core': core packages do no I/O; the caller in cmd/ or an internal/ shell package passes values in (depguard)
import "os"
       ^
internal/core/boundary_probe.go:5:5: var boundaryProbe is unused (unused)
var boundaryProbe = os.ErrNotExist
    ^
2 issues:
* depguard: 1
* unused: 1
[check:go] ERROR task failed
```

## Import-linter

Command: `mise run check:imports`. Exit status: 1. Probe: src/agent_orchestration_poc/core/import_probe.py.

```text
[check:imports] $ uv run lint-imports --no-logo
   Building agent-orchestration-poc @ file:///Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-58-boundaries-and-gates
      Built agent-orchestration-poc @ file:///Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-58-boundaries-and-gates
Uninstalled 1 package in 1ms
Installed 1 package in 1ms

---------
Contracts
---------

Analyzed 5 files, 1 dependencies.
---------------------------------

The shell imports the core; the core never imports the shell KEPT
The core does no I/O BROKEN

Contracts: 1 kept, 1 broken.


----------------
Broken contracts
----------------

The core does no I/O
--------------------

agent_orchestration_poc.core is not allowed to import os:

-   agent_orchestration_poc.core.import_probe -> os (l.3)


Core modules take values and return values. Move the call into
agent_orchestration_poc.shell and pass its result in.


[check:imports] ERROR task failed
```

## TID251

Command: `mise run check:ruff`. Exit status: 1. Probe: src/agent_orchestration_poc/core/tid_probe.py.

```text
[check:ruff] $ uv run ruff check .
TID251 `os.remove` is banned: Core packages delete nothing. Move file operations to the shell.
 --> src/agent_orchestration_poc/core/tid_probe.py:5:1
  |
3 | import os
4 |
5 | os.remove("probe")
  | ^^^^^^^^^

PTH107 `os.remove()` should be replaced by `Path.unlink()`
 --> src/agent_orchestration_poc/core/tid_probe.py:5:1
  |
3 | import os
4 |
5 | os.remove("probe")
  | ^^^^^^^^^
help: Replace with `Path(...).unlink()`

Found 2 errors.
[check:ruff] ERROR task failed
```

## jscpd

Command: `mise run check:dupl`. Exit status: 1. Probe: scripts/duplicate_probe_a.py, scripts/duplicate_probe_b.py.

```text
[check:dupl] $ jscpd --config .jscpd.json --exit-code=1 cmd internal src tests experiments scripts apps packages
Using config from .jscpd.json
Clone found (python)
 - duplicate_probe_a.py [1:1 - 22:17] (22 lines, 108 tokens)
   duplicate_probe_b.py [1:1 - 22:17]
┌────────┬────────────────┬─────────────┬──────────────┬──────────────┬──────────────────┬───────────────────┐
│ Format │ Files analyzed │ Total lines │ Total tokens │ Clones found │ Duplicated lines │ Duplicated tokens │
├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤
│ go     │ 3              │ 69          │ 316          │ 0            │ 0 (0.00%)        │ 0 (0.00%)         │
├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤
│ python │ 3              │ 69          │ 329          │ 1            │ 21 (30.43%)      │ 108 (32.83%)      │
├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤
│ Total: │ 6              │ 138         │ 645          │ 1            │ 21 (15.22%)      │ 108 (16.74%)      │
└────────┴────────────────┴─────────────┴──────────────┴──────────────┴──────────────────┴───────────────────┘
Found 1 clones.
time: 21.038ms
[check:dupl] ERROR task failed
```

## deadcode

Command: `mise run check:deadcode`. Exit status: 1. Probe: internal/version/deadcode_probe.go.

```text
[check:deadcode] $ scripts/check-deadcode.sh
internal/version/deadcode_probe.go:3:6: unreachable func: DeadcodeProbe
[check:deadcode] ERROR task failed
```

## vulture

Command: `mise run check:deadcode`. Exit status: 3. Probe: src/agent_orchestration_poc/shell/vulture_probe.py.

```text
[check:deadcode] $ scripts/check-deadcode.sh
[check:deadcode] $ uv run vulture
src/agent_orchestration_poc/shell/vulture_probe.py:3: unused function 'vulture_probe' (60% confidence)
[check:deadcode] ERROR task failed
```

## Go complexity

Command: `mise run check:go`. Exit status: 1. Probe: internal/core/complexity_probe.go.

```text
[check:go] $ scripts/check-gofumpt.sh
[check:go] $ go vet ./...
[check:go] $ go mod tidy -diff
[check:go] $ go mod verify
all modules verified
[check:go] $ golangci-lint run ./...
internal/core/complexity_probe.go:3:1: cognitive complexity 16 of func `complexityProbe` is high (> 15) (gocognit)
func complexityProbe(n int) int {
^
1 issues:
* gocognit: 1
[check:go] ERROR task failed
```

## Ruff complexity

Command: `mise run check:ruff`. Exit status: 1. Probe: src/agent_orchestration_poc/shell/complexity_probe.py.

```text
[check:ruff] $ uv run ruff check .
C901 `complexity_probe` is too complex (13 > 10)
 --> src/agent_orchestration_poc/shell/complexity_probe.py:3:5
  |
1 | """Complexity probe."""
2 |
3 | def complexity_probe(value: int) -> int:
  |     ^^^^^^^^^^^^^^^^
4 |     if value == 0:
5 |         return 0
  |

PLR0911 Too many return statements (13 > 6)
 --> src/agent_orchestration_poc/shell/complexity_probe.py:3:5
  |
1 | """Complexity probe."""
2 |
3 | def complexity_probe(value: int) -> int:
  |     ^^^^^^^^^^^^^^^^
4 |     if value == 0:
5 |         return 0
  |

D103 Missing docstring in public function
 --> src/agent_orchestration_poc/shell/complexity_probe.py:3:5
  |
1 | """Complexity probe."""
2 |
3 | def complexity_probe(value: int) -> int:
  |     ^^^^^^^^^^^^^^^^
4 |     if value == 0:
5 |         return 0
  |

Found 3 errors.
[check:ruff] ERROR task failed
```
