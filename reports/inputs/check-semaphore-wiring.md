# Check semaphore wiring evidence

## Scope and sources

Issue #332 adds wrappers around `check`, `check:mutation`, `check:mutation:go`, `check:mutation:python`, and `docs:build`. The original bodies move to hidden tasks with their dependencies, working directories, environment, and command order retained. The semaphore implementation remains unchanged.

Harness: Codex CLI 0.157.1. Model: `gpt-6-astra`, medium effort. Runtime: macOS arm64, mise 2026.8.6, Python 3.14.6, pytest 9.1.1.

Documented: the lease contract comes from `.internal/scaffolding/check-semaphore/README.md` at internal commit `16921f8b5de231a77b57458611e42d6c9665d93b`. Source read: `internal/shell/checksemaphore/inherit.go` and `run.go`. The implementation checks descriptor 3 against the inherited lease path and passes the descriptor to each child.

Documented: mise task arrays run in order, dependency-only aggregates are supported, and `hide = true` hides a task from listings. Source and versioned documentation read: mise tag `v2026.8.6`, commit `71212d424cd07189b22027f496c01ccad76e8b6d`, `docs/tasks/toml-tasks.md` and dependency resolution in `src/cli/run.rs`.

The existing mise clone could not fetch a missing blob because the sandbox denied writing its Git object directory. The brief authorized cloning dependency sources into temporary storage. The pinned checkout used here is `/tmp/check-semaphore-332-mise-source`, created with:

```sh
git clone --depth 1 --branch v2026.8.6 https://github.com/jdx/mise.git /tmp/check-semaphore-332-mise-source
```

## Serialization trial

Verified: two concurrent `mise run check` processes serialize when one of the default two slots is occupied by an idle foreground command. Both runs use the real installed wrapper and the default shared host directory and capacity. No lease variable is supplied manually. This trial does not claim that a two-slot semaphore serializes two jobs when both slots are available or establishes a host load bound.

The first heavy-task output and process completion timestamps are UTC observations from the collector. Run B reports queue position 1 with the idle holder and run A occupying the two slots before B starts its heavy tasks.

| Run | Invocation | First check task | Process exit | Status |
| --- | --- | --- | --- | --- |
| A | 2026-10-08T23:08:00.811477+00:00 | 2026-10-08T23:08:01.485609+00:00 | 2026-10-08T23:09:09.295967+00:00 | 0 |
| B | 2026-10-08T23:08:00.811636+00:00 | 2026-10-08T23:09:09.606460+00:00 | 2026-10-08T23:10:26.738504+00:00 | 0 |

Exact collector, saved as `/tmp/check-semaphore-332-trial.py`:

```python
import os
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

root = Path('/tmp/check-semaphore-332-evidence')
root.mkdir(exist_ok=True)
semaphore = '/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/check-semaphore'
env = {**os.environ, 'NO_COLOR': '1'}

def run(label):
    with (root / f'{label}.log').open('w') as log:
        log.write(f'{datetime.now(UTC).isoformat()} launch mise run check\n')
        log.flush()
        child = subprocess.Popen(['mise', 'run', 'check'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in child.stdout:
            log.write(f'{datetime.now(UTC).isoformat()} {line}')
            log.flush()
        status = child.wait()
        log.write(f'{datetime.now(UTC).isoformat()} exit {status}\n')
        print(label, status, flush=True)

holder = subprocess.Popen([semaphore, '--', 'sh', '-c', 'printf "ready\\n"; read release'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
try:
    assert holder.stdout.readline() == 'ready\n'
    print('Reserved one of the default two slots', flush=True)
    threads = [threading.Thread(target=run, args=(label,)) for label in ('A', 'B')]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
finally:
    holder.communicate('release\n', timeout=10)
```

Command:

```sh
mise exec -- python /tmp/check-semaphore-332-trial.py
```

Collector output:

```text
Reserved one of the default two slots
A 0
B 0
```

Run B queue reports:

```text
2026-10-08T23:08:31.001379+00:00 check-semaphore: queue position 1; waited 30.001s; holders: sh(wrapper_pid=7149,slot=0), mise(wrapper_pid=7201,slot=1)
2026-10-08T23:09:01.002728+00:00 check-semaphore: queue position 1; waited 1m0.002s; holders: sh(wrapper_pid=7149,slot=0), mise(wrapper_pid=7201,slot=1)
```

## Check output

Verified: the initial standalone `mise run check` and both trial runs passed. The integration-enabled run passed all 1,224 tests, including 20 wrapper fixtures. The default test task separately passed 1,063 tests and omitted 161 integration tests by its existing configuration. The coverage task ran those integration tests. Wrapper fixtures cover all five tasks with installed and absent executables and status 0 or 75, including exact fallback notices. With a stub semaphore installed, a nonzero status from the wrapped command propagates with no second, unwrapped invocation. The fixtures do not make the stub semaphore itself fail; no fallback after a real semaphore error is an inference from the wrappers' `exec` structure.

Full timestamped output from trial run A:

```text
2026-10-08T23:08:00.811477+00:00 launch mise run check
2026-10-08T23:08:00.964232+00:00 [check] $ semaphore="$(git rev-parse --path-format=absolute --git-common-dir)/.…
2026-10-08T23:08:01.465034+00:00 [check:deadcode] $ scripts/check-deadcode.sh
2026-10-08T23:08:01.469042+00:00 [check:ruff] $ uv run ruff check .
2026-10-08T23:08:01.471333+00:00 [check:shell] $ shellcheck --severity=style scripts/*.sh
2026-10-08T23:08:01.472898+00:00 [check:imports] $ uv run lint-imports --no-logo
2026-10-08T23:08:01.479203+00:00 [check:dupl] $ jscpd --config .jscpd.json --exit-code=1 cmd internal src tests …
2026-10-08T23:08:01.485609+00:00 [check:go] $ scripts/check-gofumpt.sh
2026-10-08T23:08:01.487833+00:00 [check:review-identity] $ uv run pytest tests/fixtures/review_identity/test_pol…
2026-10-08T23:08:01.493656+00:00 [check:pytest] $ uv run pytest
2026-10-08T23:08:01.504633+00:00 [check:dupl] Using config from .jscpd.json
2026-10-08T23:08:01.531439+00:00 [check:ruff] All checks passed!
2026-10-08T23:08:01.561296+00:00 [check:ruff] $ uv run ruff format --check .
2026-10-08T23:08:01.609122+00:00 [check:dupl] [90mNo duplicates found.[39m
2026-10-08T23:08:01.609177+00:00 [check:dupl] [90m┌────────┬────────────────┬─────────────┬──────────────┬──────────────┬──────────────────┬───────────────────┐[39m
2026-10-08T23:08:01.609248+00:00 [check:dupl] [90m│[39m[31m Format [39m[90m│[39m[31m Files analyzed [39m[90m│[39m[31m Total lines [39m[90m│[39m[31m Total tokens [39m[90m│[39m[31m Clones found [39m[90m│[39m[31m Duplicated lines [39m[90m│[39m[31m Duplicated tokens [39m[90m│[39m
2026-10-08T23:08:01.609280+00:00 [check:dupl] [90m├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤[39m
2026-10-08T23:08:01.609296+00:00 [check:dupl] [90m│[39m go     [90m│[39m 20             [90m│[39m 2351        [90m│[39m 17414        [90m│[39m 0            [90m│[39m 0 (0.00%)        [90m│[39m 0 (0.00%)         [90m│[39m
2026-10-08T23:08:01.609311+00:00 [check:dupl] [90m├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤[39m
2026-10-08T23:08:01.609327+00:00 [check:dupl] [90m│[39m python [90m│[39m 98             [90m│[39m 28492       [90m│[39m 178672       [90m│[39m 0            [90m│[39m 0 (0.00%)        [90m│[39m 0 (0.00%)         [90m│[39m
2026-10-08T23:08:01.609341+00:00 [check:dupl] [90m├────────┼────────────────┼─────────────┼──────────────┼──────────────┼──────────────────┼───────────────────┤[39m
2026-10-08T23:08:01.609357+00:00 [check:dupl] [90m│[39m [1mTotal:[22m [90m│[39m 118            [90m│[39m 30843       [90m│[39m 196086       [90m│[39m 0            [90m│[39m 0 (0.00%)        [90m│[39m 0 (0.00%)         [90m│[39m
2026-10-08T23:08:01.609373+00:00 [check:dupl] [90m└────────┴────────────────┴─────────────┴──────────────┴──────────────┴──────────────────┴───────────────────┘[39m
2026-10-08T23:08:01.609411+00:00 [check:dupl] [90mFound 0 clones.[39m
2026-10-08T23:08:01.609420+00:00 [check:dupl] [90mtime: 101.823ms[39m
2026-10-08T23:08:01.609429+00:00 [check:dupl]
2026-10-08T23:08:01.609439+00:00 [check:dupl] [90m💡 Auto-refactor with AI: [1m[39mnpx skills add https://github.com/kucherenko/jscpd --skill dry-refactoring[90m[22m
2026-10-08T23:08:01.609453+00:00 [check:dupl] [90m🎩 New: Gangsta Agents — discipline your AI coding → gangsta.page[39m
2026-10-08T23:08:01.609465+00:00 [check:dupl] [90m💖 Support jscpd project → https://opencollective.com/jscpd[39m
2026-10-08T23:08:01.642899+00:00 [check:coverage] $ mkdir -p .coverage-reports
2026-10-08T23:08:01.658990+00:00 [check:ruff] 126 files already formatted
2026-10-08T23:08:01.668688+00:00 [check:coverage] $ uv run --group analysis pytest --run-integration --cov=agent…
2026-10-08T23:08:01.707311+00:00 [check:go] $ scripts/test-go-format.sh
2026-10-08T23:08:01.735666+00:00 [check:pyrefly] $ uv run pyrefly check --search-path scaffolding/github-monitor
2026-10-08T23:08:01.851019+00:00 [check:pyrefly]  WARN PYTHONPATH environment variable is set to `scaffolding/worker-messaging`. Checks in other environments may not include these paths.
2026-10-08T23:08:01.903477+00:00 [check:pyrefly]  INFO Checking project configured at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/pyproject.toml`
2026-10-08T23:08:01.910588+00:00 [check:pyrefly]  WARN Skipping include pattern `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/**/*.ipynb` because it is matched by `project-excludes` or an ignore file.
2026-10-08T23:08:01.910630+00:00 [check:pyrefly] `project-excludes`: [/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/research/imported, /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/design-sketch, /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/.holding, **/node_modules, **/__pycache__, **/venv/**/*, /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/scaffolding/worker-messaging, /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/.venv/lib/python3.14/site-packages], ignore files [/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore/.gitignore, /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.git/info/exclude]
2026-10-08T23:08:01.950175+00:00 [check:imports]
2026-10-08T23:08:01.951870+00:00 [check:imports] ---------
2026-10-08T23:08:01.952828+00:00 [check:imports] Contracts
2026-10-08T23:08:01.954330+00:00 [check:imports] ---------
2026-10-08T23:08:01.954734+00:00 [check:imports]
2026-10-08T23:08:01.955020+00:00 [check:imports] Analyzed 67 files, 187 dependencies.
2026-10-08T23:08:01.955166+00:00 [check:imports] ------------------------------------
2026-10-08T23:08:01.955407+00:00 [check:imports]
2026-10-08T23:08:01.959148+00:00 [check:imports] The shell imports the core; the core never imports the shell KEPT
2026-10-08T23:08:01.959969+00:00 [check:imports] The core does no I/O KEPT
2026-10-08T23:08:01.960332+00:00 [check:imports]
2026-10-08T23:08:01.960366+00:00 [check:imports] Contracts: 2 kept, 0 broken.
2026-10-08T23:08:02.050132+00:00 [check:biome] $ biome check --no-errors-on-unmatched .
2026-10-08T23:08:02.275033+00:00 [check:biome] Checked 176 files in 99ms. No fixes applied.
2026-10-08T23:08:02.299333+00:00 [check:vale] $ scripts/check-vale.sh
2026-10-08T23:08:02.535444+00:00 [check:pyrefly]  INFO 0 diagnostics (15 suppressed)
2026-10-08T23:08:02.557741+00:00 [check:rumdl] $ rumdl check .
2026-10-08T23:08:02.801494+00:00 [check:shell] $ shfmt -d -i 4 -ci scripts/*.sh
2026-10-08T23:08:02.901865+00:00 [check:ryl] $ ryl check .
2026-10-08T23:08:03.031695+00:00 [check:rumdl]
2026-10-08T23:08:03.031735+00:00 [check:rumdl] Success: No issues found in 230 files (188ms)
2026-10-08T23:08:03.032959+00:00 [check:review-identity] ============================= test session starts ==============================
2026-10-08T23:08:03.032994+00:00 [check:review-identity] platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
2026-10-08T23:08:03.033007+00:00 [check:review-identity] rootdir: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
2026-10-08T23:08:03.033017+00:00 [check:review-identity] configfile: pyproject.toml
2026-10-08T23:08:03.033025+00:00 [check:review-identity] plugins: platformdirs-4.12.0, hypothesis-6.168.1, cov-7.0.0
2026-10-08T23:08:03.033033+00:00 [check:review-identity] collected 43 items
2026-10-08T23:08:03.033050+00:00 [check:review-identity]
2026-10-08T23:08:03.046493+00:00 [check:tombi] $ tombi lint
2026-10-08T23:08:03.081877+00:00 [check:review-identity] tests/fixtures/review_identity/test_policy.py .......................... [ 60%]
2026-10-08T23:08:03.144387+00:00 [check:guard-markdown] $ scripts/markdown-files.sh | xargs -r guard-markdown
2026-10-08T23:08:03.238627+00:00 [check:tombi] 9 files linted successfully
2026-10-08T23:08:03.257222+00:00 [check:tombi] $ tombi format --check
2026-10-08T23:08:03.484880+00:00 [check:tombi] 9 files did not need formatting
2026-10-08T23:08:03.500034+00:00 [check:mermaid] $ scripts/check-mermaid.sh
2026-10-08T23:08:03.576221+00:00 [check:experiments] $ scripts/check-experiments.sh
2026-10-08T23:08:03.662901+00:00 [check:ignore-collisions] $ scripts/check-ignore-collisions.sh
2026-10-08T23:08:03.742314+00:00 [check:pytest] ============================= test session starts ==============================
2026-10-08T23:08:03.742340+00:00 [check:pytest] platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
2026-10-08T23:08:03.742349+00:00 [check:pytest] rootdir: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
2026-10-08T23:08:03.742355+00:00 [check:pytest] configfile: pyproject.toml
2026-10-08T23:08:03.742360+00:00 [check:pytest] testpaths: tests
2026-10-08T23:08:03.742366+00:00 [check:pytest] plugins: platformdirs-4.12.0, hypothesis-6.168.1, cov-7.0.0
2026-10-08T23:08:03.742374+00:00 [check:pytest] collected 1224 items
2026-10-08T23:08:03.742441+00:00 [check:pytest]
2026-10-08T23:08:03.759077+00:00 [check:pytest] tests/fixtures/review_identity/test_policy.py .......................... [  2%]
2026-10-08T23:08:03.913455+00:00 [check:review-identity] ...........                                                              [ 86%]
2026-10-08T23:08:03.956946+00:00 [check:go] $ go vet ./...
2026-10-08T23:08:04.055089+00:00 [check:coverage] ============================= test session starts ==============================
2026-10-08T23:08:04.055484+00:00 [check:coverage] platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
2026-10-08T23:08:04.055508+00:00 [check:coverage] rootdir: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
2026-10-08T23:08:04.055517+00:00 [check:coverage] configfile: pyproject.toml
2026-10-08T23:08:04.055525+00:00 [check:coverage] testpaths: tests
2026-10-08T23:08:04.055542+00:00 [check:coverage] plugins: platformdirs-4.12.0, hypothesis-6.168.1, cov-7.0.0
2026-10-08T23:08:04.055549+00:00 [check:coverage] collected 1224 items
2026-10-08T23:08:04.055556+00:00 [check:coverage]
2026-10-08T23:08:04.083298+00:00 [check:coverage] tests/fixtures/review_identity/test_policy.py .......................... [  2%]
2026-10-08T23:08:04.603156+00:00 [check:go] $ go mod tidy -diff
2026-10-08T23:08:04.730830+00:00 [check:go] $ go mod verify
2026-10-08T23:08:05.091913+00:00 [check:pytest] ...........                                                              [  3%]
2026-10-08T23:08:05.098684+00:00 [check:pytest] tests/fixtures/review_identity/test_wrapper.py ssssss                    [  3%]
2026-10-08T23:08:05.299329+00:00 [check:go] all modules verified
2026-10-08T23:08:05.301417+00:00 [check:go] $ golangci-lint run ./...
2026-10-08T23:08:05.403943+00:00 [check:coverage] ...........                                                              [  3%]
2026-10-08T23:08:05.679779+00:00 [check:pytest] tests/test_analysis_notebooks.py .......................s.............ss [  6%]
2026-10-08T23:08:05.689261+00:00 [check:pytest] ssssssssssssssssssssss                                                   [  8%]
2026-10-08T23:08:05.700328+00:00 [check:pytest] tests/test_check_semaphore.py ssssssssssssssssssss                       [ 10%]
2026-10-08T23:08:05.717175+00:00 [check:pytest] tests/test_coordinator_preflight.py ................................     [ 12%]
2026-10-08T23:08:05.718856+00:00 [check:pytest] tests/test_coordinator_preflight_shell.py sss                            [ 12%]
2026-10-08T23:08:05.724226+00:00 [check:pytest] tests/test_coverage_floors.py .......                                    [ 13%]
2026-10-08T23:08:05.891674+00:00 [check:pytest] tests/test_gate_changes.py ............................................. [ 17%]
2026-10-08T23:08:06.520704+00:00 [check:go] 0 issues.
2026-10-08T23:08:06.539516+00:00 [check:go] $ go build ./...
2026-10-08T23:08:06.900774+00:00 [check:pytest] ..............................................................s          [ 22%]
2026-10-08T23:08:06.903045+00:00 [check:pytest] tests/test_go_branch_coverage_shell.py ssss                              [ 22%]
2026-10-08T23:08:06.906505+00:00 [check:pytest] tests/test_gremlins_output.py ....                                       [ 23%]
2026-10-08T23:08:07.106941+00:00 [check:deadcode] $ uv run vulture
2026-10-08T23:08:07.217578+00:00 [check:review-identity] tests/fixtures/review_identity/test_wrapper.py ......                    [100%]
2026-10-08T23:08:07.217611+00:00 [check:review-identity]
2026-10-08T23:08:07.217621+00:00 [check:review-identity] ============================== 43 passed in 4.85s ==============================
2026-10-08T23:08:07.312946+00:00 [check:handoff-classifier] $ scripts/test-handoff-pr-classifier.sh
2026-10-08T23:08:07.359516+00:00 [check:handoff-classifier] handoff classifier fixtures ok
2026-10-08T23:08:07.371677+00:00 [check:secrets] $ gitleaks git --redact --no-banner .
2026-10-08T23:08:07.708344+00:00 [check:pytest] tests/test_host_socket_attribution.py .................................. [ 25%]
2026-10-08T23:08:07.823421+00:00 [check:pytest] ......................ssssssssss                                         [ 28%]
2026-10-08T23:08:07.830176+00:00 [check:pytest] tests/test_mutation_score.py ...........                                 [ 29%]
2026-10-08T23:08:07.831747+00:00 [check:pytest] tests/test_operator_command_shell.py sss                                 [ 29%]
2026-10-08T23:08:07.974912+00:00 [check:pytest] tests/test_operator_commands.py ........................................ [ 32%]
2026-10-08T23:08:08.306985+00:00 [check:go] $ go test -race -shuffle=on ./...
2026-10-08T23:08:08.750287+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/cmd/agentctl	[no test files]
2026-10-08T23:08:08.804031+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/cmd/agentd	[no test files]
2026-10-08T23:08:08.804059+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/api	[no test files]
2026-10-08T23:08:08.804068+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/backend/container	[no test files]
2026-10-08T23:08:08.804075+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/backend/tmux	[no test files]
2026-10-08T23:08:09.125890+00:00 [check:actions] $ actionlint
2026-10-08T23:08:09.321740+00:00 [notebooks:lint] $ uv run --group analysis python -m agent_orchestration_poc.sh…
2026-10-08T23:08:09.738674+00:00 [check:pytest] ............                                                             [ 33%]
2026-10-08T23:08:09.747773+00:00 [check:pytest] tests/test_package.py .s                                                 [ 33%]
2026-10-08T23:08:09.907557+00:00 [check:pytest] tests/test_parent_link_sync.py ...........                               [ 34%]
2026-10-08T23:08:10.070140+00:00 [notebooks:lint] ✔ 0 errors, 0 warnings and 0 suggestions in 1 file.
2026-10-08T23:08:10.075231+00:00 [check:pytest] tests/test_parent_link_sync_shell.py ..sssss..                           [ 35%]
2026-10-08T23:08:10.132580+00:00 [notebooks:lint]
2026-10-08T23:08:10.133081+00:00 [notebooks:lint] Success: No issues found in 1 file (17ms)
2026-10-08T23:08:10.188438+00:00 [notebooks:lint] All checks passed!
2026-10-08T23:08:10.362856+00:00 [check:coverage] tests/fixtures/review_identity/test_wrapper.py ......                    [  3%]
2026-10-08T23:08:10.462022+00:00 [notebooks:lint] ✔ 0 errors, 0 warnings and 0 suggestions in 1 file.
2026-10-08T23:08:10.490504+00:00 [notebooks:lint]
2026-10-08T23:08:10.490536+00:00 [notebooks:lint] Success: No issues found in 1 file (10ms)
2026-10-08T23:08:10.492716+00:00 [check:mermaid] mermaid: 9 block(s) in 227 file(s), 0 invalid
2026-10-08T23:08:10.517035+00:00 [check:workflow-forms] $ uv run pytest tests/test_workflow_forms.py
2026-10-08T23:08:10.548265+00:00 [notebooks:lint] All checks passed!
2026-10-08T23:08:10.736284+00:00 [notebooks:lint] ✔ 0 errors, 0 warnings and 0 suggestions in 1 file.
2026-10-08T23:08:10.776069+00:00 [notebooks:lint]
2026-10-08T23:08:10.776106+00:00 [notebooks:lint] Success: No issues found in 1 file (12ms)
2026-10-08T23:08:10.825739+00:00 [check:secrets] 7:08PM INF 504 commits scanned.
2026-10-08T23:08:10.825774+00:00 [check:secrets] 7:08PM INF scanned ~26088382 bytes (26.09 MB) in 3.01s
2026-10-08T23:08:10.825792+00:00 [check:secrets] 7:08PM INF no leaks found
2026-10-08T23:08:10.841862+00:00 [check:gate-changes] $ uv run python -m agent_orchestration_poc.shell.gate_chan…
2026-10-08T23:08:10.895722+00:00 [notebooks:lint] All checks passed!
2026-10-08T23:08:10.935379+00:00 [check:pr-size-contract] $ uv run pytest tests/test_pr_size.py --run-integratio…
2026-10-08T23:08:10.999250+00:00 [check:gate-changes] Gate comparison skipped outside a pull request
2026-10-08T23:08:11.021843+00:00 [check:coverage] tests/test_analysis_notebooks.py ....................................... [  6%]
2026-10-08T23:08:11.286401+00:00 [check:workflow-forms] ============================= test session starts ==============================
2026-10-08T23:08:11.286440+00:00 [check:workflow-forms] platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
2026-10-08T23:08:11.286451+00:00 [check:workflow-forms] rootdir: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
2026-10-08T23:08:11.286474+00:00 [check:workflow-forms] configfile: pyproject.toml
2026-10-08T23:08:11.286486+00:00 [check:workflow-forms] plugins: platformdirs-4.12.0, hypothesis-6.168.1, cov-7.0.0
2026-10-08T23:08:11.286494+00:00 [check:workflow-forms] collected 113 items
2026-10-08T23:08:11.286502+00:00 [check:workflow-forms]
2026-10-08T23:08:11.321440+00:00 [check:workflow-forms] tests/test_workflow_forms.py ........................................... [ 38%]
2026-10-08T23:08:11.617268+00:00 [check:pytest] tests/test_pr_size.py ...............................................sss [ 39%]
2026-10-08T23:08:11.626340+00:00 [check:pytest] sssssssssssssssssss                                                      [ 41%]
2026-10-08T23:08:11.663114+00:00 [check:pytest] tests/test_preflight_claude_interactive.py ..........                    [ 42%]
2026-10-08T23:08:11.789011+00:00 [check:pr-size-contract] ============================= test session starts ==============================
2026-10-08T23:08:11.789050+00:00 [check:pr-size-contract] platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
2026-10-08T23:08:11.789060+00:00 [check:pr-size-contract] rootdir: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
2026-10-08T23:08:11.789075+00:00 [check:pr-size-contract] configfile: pyproject.toml
2026-10-08T23:08:11.789084+00:00 [check:pr-size-contract] plugins: platformdirs-4.12.0, hypothesis-6.168.1, cov-7.0.0
2026-10-08T23:08:11.789091+00:00 [check:pr-size-contract] collected 69 items
2026-10-08T23:08:11.789112+00:00 [check:pr-size-contract]
2026-10-08T23:08:11.978256+00:00 [check:workflow-forms] ......................................................................   [100%]
2026-10-08T23:08:11.978294+00:00 [check:workflow-forms]
2026-10-08T23:08:11.978307+00:00 [check:workflow-forms] ============================= 113 passed in 1.03s ==============================
2026-10-08T23:08:12.073198+00:00 [check:workflow-forms] $ uv run python -m agent_orchestration_poc.shell.workflo…
2026-10-08T23:08:12.583852+00:00 [check:pytest] tests/test_project_probe.py .........................................    [ 45%]
2026-10-08T23:08:12.801254+00:00 [check:pytest] tests/test_project_rank.py ..........................                    [ 47%]
2026-10-08T23:08:12.812281+00:00 [check:pytest] tests/test_project_rank_shell.py ssssssss                                [ 48%]
2026-10-08T23:08:12.876805+00:00 [check:pr-size-contract] tests/test_pr_size.py ...............................................{"counted_units": 0, "exclusion_reason": "path:uv.lock", "fixture": "lockfile-only", "old_path": null, "path": "uv.lock", "raw_added": 2, "raw_deleted": 0, "verdict": "pass"}
2026-10-08T23:08:12.926701+00:00 [check:pr-size-contract] .{"counted_units": 0, "exclusion_reason": "scc:generated", "fixture": "generated", "old_path": null, "path": "src/generated.py", "raw_added": 2, "raw_deleted": 0, "verdict": "pass"}
2026-10-08T23:08:13.005113+00:00 [check:pr-size-contract] .{"counted_units": 2, "exclusion_reason": null, "fixture": "rename", "old_path": "src/old.py", "path": "src/new.py", "raw_added": 1, "raw_deleted": 1, "verdict": "pass"}
2026-10-08T23:08:13.041141+00:00 [check:pr-size-contract] .{"counted_units": 1, "exclusion_reason": null, "fixture": "deletion", "old_path": null, "path": "src/gone.py", "raw_added": 0, "raw_deleted": 2, "verdict": "pass"}
2026-10-08T23:08:13.116613+00:00 [check:pr-size-contract] .{"counted_units": 0, "exclusion_reason": null, "fixture": "comment-only", "old_path": null, "path": "src/note.py", "raw_added": 1, "raw_deleted": 1, "verdict": "pass"}
2026-10-08T23:08:13.188011+00:00 [check:pr-size-contract] .{"counted_units": 2, "exclusion_reason": null, "fixture": "multiline-comment-fragment", "old_path": null, "path": "src/note.js", "raw_added": 1, "raw_deleted": 1, "verdict": "pass"}
2026-10-08T23:08:13.260743+00:00 [check:pr-size-contract] .{"counted_units": 3, "exclusion_reason": null, "fixture": "documentation-only", "old_path": null, "path": "docs/page.md", "raw_added": 2, "raw_deleted": 1, "verdict": "pass"}
2026-10-08T23:08:13.331921+00:00 [check:pr-size-contract] .{"counted_units": 2, "exclusion_reason": null, "fixture": "mixed", "old_path": null, "path": "src/mixed.py", "raw_added": 3, "raw_deleted": 2, "verdict": "pass"}
2026-10-08T23:08:13.372751+00:00 [check:pr-size-contract] .{"counted_units": 0, "exclusion_reason": "scc:minified", "fixture": "minified", "old_path": null, "path": "web/bundle.js", "raw_added": 1, "raw_deleted": 0, "verdict": "pass"}
2026-10-08T23:08:13.413005+00:00 [check:ignore-collisions] case-insensitive directory match: /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.git/info/exclude:21:/.codex/ -> research/imported/agent-peering-tests/.codex
2026-10-08T23:08:13.415226+00:00 [check:ignore-collisions] $ scripts/test-ignore-collisions.sh
2026-10-08T23:08:13.422231+00:00 [check:pr-size-contract] .{"counted_units": 801, "exclusion_reason": null, "fixture": "over-limit", "old_path": null, "path": "src/large.py", "raw_added": 801, "raw_deleted": 0, "verdict": "fail"}
2026-10-08T23:08:13.572798+00:00 [check:ignore-collisions] negated fixture: exit 0
2026-10-08T23:08:13.668836+00:00 [check:ignore-collisions] ignored fixture: exit 1
2026-10-08T23:08:13.668871+00:00 [check:ignore-collisions] ignored tracked path: .gitignore:1:*.txt	blocked.txt
2026-10-08T23:08:13.668885+00:00 [check:ignore-collisions] ignore collision fixtures ok
2026-10-08T23:08:15.880818+00:00 [check:pytest] tests/test_relay_cell.py ..........................................ssss. [ 52%]
2026-10-08T23:08:15.895053+00:00 [check:pytest] ..ss.....s                                                               [ 52%]
2026-10-08T23:08:15.922420+00:00 [check:pytest] tests/test_skipscan.py ................................................. [ 56%]
2026-10-08T23:08:16.152772+00:00 [check:pytest] ........................................................................ [ 62%]
2026-10-08T23:08:16.370867+00:00 [check:pytest] ..............................                                           [ 65%]
2026-10-08T23:08:16.388927+00:00 [check:pytest] tests/test_skipscan_events.py ......................                     [ 66%]
2026-10-08T23:08:16.392656+00:00 [check:pytest] tests/test_skipscan_shell.py ssssss.                                     [ 67%]
2026-10-08T23:08:16.747417+00:00 [check:pytest] tests/test_subject.py ....................                               [ 69%]
2026-10-08T23:08:16.829286+00:00 [check:pytest] tests/test_transcript_retro.py .............................s.....ss.    [ 72%]
2026-10-08T23:08:17.192393+00:00 [check:pytest] tests/test_work_model_backfill.py ...................................... [ 75%]
2026-10-08T23:08:17.193079+00:00 [check:pr-size-contract] .............
2026-10-08T23:08:17.193121+00:00 [check:pr-size-contract]
2026-10-08T23:08:17.193133+00:00 [check:pr-size-contract] ============================== 69 passed in 5.77s ==============================
2026-10-08T23:08:17.566920+00:00 [check:pytest] ............................................................             [ 80%]
2026-10-08T23:08:17.690781+00:00 [check:pytest] tests/test_work_model_backfill_executor.py ............................. [ 82%]
2026-10-08T23:08:17.706942+00:00 [check:pytest] ......................                                                   [ 84%]
2026-10-08T23:08:17.755512+00:00 [check:pytest] tests/test_work_model_backfill_rollback.py ............................. [ 86%]
2026-10-08T23:08:17.755820+00:00 [check:pytest]                                                                          [ 86%]
2026-10-08T23:08:17.762435+00:00 [check:pytest] tests/test_work_model_backfill_shell.py sssssssss.ssssssssssss           [ 88%]
2026-10-08T23:08:17.782871+00:00 [check:pytest] tests/test_workflow_forms.py ........................................... [ 92%]
2026-10-08T23:08:17.972422+00:00 [check:coverage] ......................                                                   [  8%]
2026-10-08T23:08:18.034714+00:00 [check:pytest] ......................................................................   [ 97%]
2026-10-08T23:08:18.038687+00:00 [check:pytest] tests/test_workflow_forms_shell.py ssssssssssssss                        [ 99%]
2026-10-08T23:08:18.091269+00:00 [check:pytest] tests/test_workflow_new_issue.py ..........ss                            [100%]
2026-10-08T23:08:18.091304+00:00 [check:pytest]
2026-10-08T23:08:18.091313+00:00 [check:pytest] =========================== short test summary info ============================
2026-10-08T23:08:18.091321+00:00 [check:pytest] SKIPPED [6] tests/fixtures/review_identity/test_wrapper.py:18: needs --run-integration
2026-10-08T23:08:18.091329+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:104: needs --run-integration
2026-10-08T23:08:18.091337+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:153: needs --run-integration
2026-10-08T23:08:18.091343+00:00 [check:pytest] SKIPPED [3] tests/test_analysis_notebooks.py:169: needs --run-integration
2026-10-08T23:08:18.091350+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:182: needs --run-integration
2026-10-08T23:08:18.091356+00:00 [check:pytest] SKIPPED [12] tests/test_analysis_notebooks.py:193: needs --run-integration
2026-10-08T23:08:18.091363+00:00 [check:pytest] SKIPPED [2] tests/test_analysis_notebooks.py:235: needs --run-integration
2026-10-08T23:08:18.091369+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:258: needs --run-integration
2026-10-08T23:08:18.091376+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:271: needs --run-integration
2026-10-08T23:08:18.091391+00:00 [check:pytest] SKIPPED [2] tests/test_analysis_notebooks.py:282: needs --run-integration
2026-10-08T23:08:18.091398+00:00 [check:pytest] SKIPPED [1] tests/test_analysis_notebooks.py:300: needs --run-integration
2026-10-08T23:08:18.091404+00:00 [check:pytest] SKIPPED [20] tests/test_check_semaphore.py:20: needs --run-integration
2026-10-08T23:08:18.091410+00:00 [check:pytest] SKIPPED [1] tests/test_coordinator_preflight_shell.py:29: needs --run-integration
2026-10-08T23:08:18.091417+00:00 [check:pytest] SKIPPED [1] tests/test_coordinator_preflight_shell.py:41: needs --run-integration
2026-10-08T23:08:18.091423+00:00 [check:pytest] SKIPPED [1] tests/test_coordinator_preflight_shell.py:65: needs --run-integration
2026-10-08T23:08:18.091429+00:00 [check:pytest] SKIPPED [1] tests/test_gate_changes.py:621: needs --run-integration
2026-10-08T23:08:18.091436+00:00 [check:pytest] SKIPPED [1] tests/test_go_branch_coverage_shell.py:17: needs --run-integration
2026-10-08T23:08:18.091441+00:00 [check:pytest] SKIPPED [2] tests/test_go_branch_coverage_shell.py:43: needs --run-integration
2026-10-08T23:08:18.091448+00:00 [check:pytest] SKIPPED [1] tests/test_go_branch_coverage_shell.py:71: needs --run-integration
2026-10-08T23:08:18.091454+00:00 [check:pytest] SKIPPED [4] tests/test_host_socket_attribution.py:636: needs --run-integration
2026-10-08T23:08:18.091461+00:00 [check:pytest] SKIPPED [4] tests/test_host_socket_attribution.py:754: needs --run-integration
2026-10-08T23:08:18.091468+00:00 [check:pytest] SKIPPED [1] tests/test_host_socket_attribution.py:841: needs --run-integration
2026-10-08T23:08:18.091475+00:00 [check:pytest] SKIPPED [1] tests/test_host_socket_attribution.py:889: needs --run-integration
2026-10-08T23:08:18.091481+00:00 [check:pytest] SKIPPED [2] tests/test_operator_command_shell.py:93: needs --run-integration
2026-10-08T23:08:18.091488+00:00 [check:pytest] SKIPPED [1] tests/test_operator_command_shell.py:138: needs --run-integration
2026-10-08T23:08:18.091494+00:00 [check:pytest] SKIPPED [1] tests/test_package.py:13: needs --run-integration
2026-10-08T23:08:18.091500+00:00 [check:pytest] SKIPPED [4] tests/test_parent_link_sync_shell.py:70: needs --run-integration
2026-10-08T23:08:18.091506+00:00 [check:pytest] SKIPPED [1] tests/test_parent_link_sync_shell.py:110: needs --run-integration
2026-10-08T23:08:18.091512+00:00 [check:pytest] SKIPPED [10] tests/test_pr_size.py:273: needs --run-integration
2026-10-08T23:08:18.091518+00:00 [check:pytest] SKIPPED [1] tests/test_pr_size.py:319: needs --run-integration
2026-10-08T23:08:18.091524+00:00 [check:pytest] SKIPPED [1] tests/test_pr_size.py:347: needs --run-integration
2026-10-08T23:08:18.091530+00:00 [check:pytest] SKIPPED [1] tests/test_pr_size.py:367: needs --run-integration
2026-10-08T23:08:18.091537+00:00 [check:pytest] SKIPPED [8] tests/test_pr_size.py:392: needs --run-integration
2026-10-08T23:08:18.091569+00:00 [check:pytest] SKIPPED [1] tests/test_pr_size.py:433: needs --run-integration
2026-10-08T23:08:18.091587+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:38: needs --run-integration
2026-10-08T23:08:18.091595+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:63: needs --run-integration
2026-10-08T23:08:18.091602+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:93: needs --run-integration
2026-10-08T23:08:18.091607+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:208: needs --run-integration
2026-10-08T23:08:18.091613+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:216: needs --run-integration
2026-10-08T23:08:18.091618+00:00 [check:pytest] SKIPPED [2] tests/test_project_rank_shell.py:224: needs --run-integration
2026-10-08T23:08:18.091622+00:00 [check:pytest] SKIPPED [1] tests/test_project_rank_shell.py:246: needs --run-integration
2026-10-08T23:08:18.091627+00:00 [check:pytest] SKIPPED [4] tests/test_relay_cell.py:615: needs --run-integration
2026-10-08T23:08:18.091632+00:00 [check:pytest] SKIPPED [1] tests/test_relay_cell.py:698: needs --run-integration
2026-10-08T23:08:18.091651+00:00 [check:pytest] SKIPPED [1] tests/test_relay_cell.py:710: needs --run-integration
2026-10-08T23:08:18.091656+00:00 [check:pytest] SKIPPED [1] tests/test_relay_cell.py:848: needs --run-integration
2026-10-08T23:08:18.091661+00:00 [check:pytest] SKIPPED [6] tests/test_skipscan_shell.py:93: needs --run-integration
2026-10-08T23:08:18.091666+00:00 [check:pytest] SKIPPED [1] tests/test_transcript_retro.py:455: needs --run-integration
2026-10-08T23:08:18.091670+00:00 [check:pytest] SKIPPED [2] tests/test_transcript_retro.py:514: needs --run-integration
2026-10-08T23:08:18.091675+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:80: needs --run-integration
2026-10-08T23:08:18.091679+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:222: needs --run-integration
2026-10-08T23:08:18.091683+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:245: needs --run-integration
2026-10-08T23:08:18.091688+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:260: needs --run-integration
2026-10-08T23:08:18.091692+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:295: needs --run-integration
2026-10-08T23:08:18.091696+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:337: needs --run-integration
2026-10-08T23:08:18.091701+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:425: needs --run-integration
2026-10-08T23:08:18.091705+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:474: needs --run-integration
2026-10-08T23:08:18.091710+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:495: needs --run-integration
2026-10-08T23:08:18.091714+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:574: needs --run-integration
2026-10-08T23:08:18.091718+00:00 [check:pytest] SKIPPED [3] tests/test_work_model_backfill_shell.py:677: needs --run-integration
2026-10-08T23:08:18.091722+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:764: needs --run-integration
2026-10-08T23:08:18.091727+00:00 [check:pytest] SKIPPED [2] tests/test_work_model_backfill_shell.py:825: needs --run-integration
2026-10-08T23:08:18.091731+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:899: needs --run-integration
2026-10-08T23:08:18.091735+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:954: needs --run-integration
2026-10-08T23:08:18.091740+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:1009: needs --run-integration
2026-10-08T23:08:18.091744+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:1075: needs --run-integration
2026-10-08T23:08:18.091748+00:00 [check:pytest] SKIPPED [1] tests/test_work_model_backfill_shell.py:1196: needs --run-integration
2026-10-08T23:08:18.091752+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:21: needs --run-integration
2026-10-08T23:08:18.091756+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:46: needs --run-integration
2026-10-08T23:08:18.091761+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:89: needs --run-integration
2026-10-08T23:08:18.091765+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:102: needs --run-integration
2026-10-08T23:08:18.091769+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:127: needs --run-integration
2026-10-08T23:08:18.091773+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:144: needs --run-integration
2026-10-08T23:08:18.091777+00:00 [check:pytest] SKIPPED [2] tests/test_workflow_forms_shell.py:159: needs --run-integration
2026-10-08T23:08:18.091782+00:00 [check:pytest] SKIPPED [5] tests/test_workflow_forms_shell.py:196: needs --run-integration
2026-10-08T23:08:18.091786+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_forms_shell.py:230: needs --run-integration
2026-10-08T23:08:18.091790+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_new_issue.py:97: needs --run-integration
2026-10-08T23:08:18.091801+00:00 [check:pytest] SKIPPED [1] tests/test_workflow_new_issue.py:107: needs --run-integration
2026-10-08T23:08:18.091806+00:00 [check:pytest] ====================== 1063 passed, 161 skipped in 15.73s ======================
2026-10-08T23:08:25.783694+00:00 [check:vale] ✔ 0 errors, 0 warnings and 0 suggestions in 227 files.
2026-10-08T23:08:27.366122+00:00 [check:coverage] tests/test_check_semaphore.py ....................                       [ 10%]
2026-10-08T23:08:27.375374+00:00 [check:coverage] tests/test_coordinator_preflight.py ................................     [ 12%]
2026-10-08T23:08:29.084839+00:00 [check:coverage] tests/test_coordinator_preflight_shell.py ...                            [ 12%]
2026-10-08T23:08:29.087126+00:00 [check:coverage] tests/test_coverage_floors.py .......                                    [ 13%]
2026-10-08T23:08:29.147338+00:00 [check:coverage] tests/test_gate_changes.py ............................................. [ 17%]
2026-10-08T23:08:29.557965+00:00 [check:coverage] ...............................................................          [ 22%]
2026-10-08T23:08:29.921945+00:00 [check:coverage] tests/test_go_branch_coverage_shell.py ....                              [ 22%]
2026-10-08T23:08:29.923632+00:00 [check:coverage] tests/test_gremlins_output.py ....                                       [ 23%]
2026-10-08T23:08:30.130043+00:00 [check:coverage] tests/test_host_socket_attribution.py .................................. [ 25%]
2026-10-08T23:08:31.251562+00:00 [check:coverage] ................................                                         [ 28%]
2026-10-08T23:08:31.255661+00:00 [check:coverage] tests/test_mutation_score.py ...........                                 [ 29%]
2026-10-08T23:08:32.811193+00:00 [check:coverage] tests/test_operator_command_shell.py ...                                 [ 29%]
2026-10-08T23:08:32.846920+00:00 [check:coverage] tests/test_operator_commands.py ........................................ [ 32%]
2026-10-08T23:08:33.013847+00:00 [check:coverage] ............                                                             [ 33%]
2026-10-08T23:08:33.014405+00:00 [check:coverage] tests/test_package.py ..                                                 [ 33%]
2026-10-08T23:08:33.032310+00:00 [check:coverage] tests/test_parent_link_sync.py ...........                               [ 34%]
2026-10-08T23:08:34.370161+00:00 [check:coverage] tests/test_parent_link_sync_shell.py .........                           [ 35%]
2026-10-08T23:08:34.793591+00:00 [check:coverage] tests/test_pr_size.py .................................................. [ 39%]
2026-10-08T23:08:37.382023+00:00 [check:coverage] ...................                                                      [ 41%]
2026-10-08T23:08:37.392791+00:00 [check:coverage] tests/test_preflight_claude_interactive.py ..........                    [ 42%]
2026-10-08T23:08:37.722424+00:00 [check:coverage] tests/test_project_probe.py .........................................    [ 45%]
2026-10-08T23:08:37.828130+00:00 [check:coverage] tests/test_project_rank.py ..........................                    [ 47%]
2026-10-08T23:08:40.471325+00:00 [check:coverage] tests/test_project_rank_shell.py ........                                [ 48%]
2026-10-08T23:08:43.974860+00:00 [check:coverage] tests/test_relay_cell.py ............................................... [ 52%]
2026-10-08T23:08:44.705866+00:00 [check:coverage] ..........                                                               [ 52%]
2026-10-08T23:08:44.726928+00:00 [check:coverage] tests/test_skipscan.py ................................................. [ 56%]
2026-10-08T23:08:44.890649+00:00 [check:coverage] ........................................................................ [ 62%]
2026-10-08T23:08:45.030787+00:00 [check:coverage] ..............................                                           [ 65%]
2026-10-08T23:08:45.041747+00:00 [check:coverage] tests/test_skipscan_events.py ......................                     [ 66%]
2026-10-08T23:08:48.383984+00:00 [check:coverage] tests/test_skipscan_shell.py .......                                     [ 67%]
2026-10-08T23:08:48.616556+00:00 [check:coverage] tests/test_subject.py ....................                               [ 69%]
2026-10-08T23:08:48.686520+00:00 [check:coverage] tests/test_transcript_retro.py ......................................    [ 72%]
2026-10-08T23:08:48.958560+00:00 [check:coverage] tests/test_work_model_backfill.py ...................................... [ 75%]
2026-10-08T23:08:49.264690+00:00 [check:coverage] ............................................................             [ 80%]
2026-10-08T23:08:49.379204+00:00 [check:coverage] tests/test_work_model_backfill_executor.py ............................. [ 82%]
2026-10-08T23:08:49.396035+00:00 [check:coverage] ......................                                                   [ 84%]
2026-10-08T23:08:49.445456+00:00 [check:coverage] tests/test_work_model_backfill_rollback.py ............................. [ 86%]
2026-10-08T23:08:49.445831+00:00 [check:coverage]                                                                          [ 86%]
2026-10-08T23:08:52.804428+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/bus	42.554s
2026-10-08T23:08:52.804473+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/cli	1.999s
2026-10-08T23:08:52.804485+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/core	[no test files]
2026-10-08T23:08:52.804499+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/command	3.101s
2026-10-08T23:08:52.804504+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/layout	2.342s
2026-10-08T23:08:52.804509+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/perms	3.391s
2026-10-08T23:08:52.804513+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/relay	2.617s
2026-10-08T23:08:52.804516+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/subject	2.929s
2026-10-08T23:08:52.804520+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/registry	[no test files]
2026-10-08T23:08:52.804524+00:00 [check:go] ?   	github.com/tbhb/agent-orchestration-poc/internal/term	[no test files]
2026-10-08T23:08:52.804529+00:00 [check:go] ok  	github.com/tbhb/agent-orchestration-poc/internal/version	3.623s
2026-10-08T23:08:59.386869+00:00 [check:coverage] tests/test_work_model_backfill_shell.py ......................           [ 88%]
2026-10-08T23:08:59.406594+00:00 [check:coverage] tests/test_workflow_forms.py ........................................... [ 92%]
2026-10-08T23:08:59.594294+00:00 [check:coverage] ......................................................................   [ 97%]
2026-10-08T23:08:59.604750+00:00 [check:coverage] tests/test_workflow_forms_shell.py ..............                        [ 99%]
2026-10-08T23:09:01.045699+00:00 [check:coverage] tests/test_workflow_new_issue.py ............                            [100%]
2026-10-08T23:09:01.045741+00:00 [check:coverage]
2026-10-08T23:09:01.045758+00:00 [check:coverage] ================================ tests coverage ================================
2026-10-08T23:09:01.045769+00:00 [check:coverage] _______________ coverage: platform darwin, python 3.14.6-final-0 _______________
2026-10-08T23:09:01.045780+00:00 [check:coverage]
2026-10-08T23:09:01.045790+00:00 [check:coverage] Name                                                               Stmts   Miss Branch BrPart  Cover
2026-10-08T23:09:01.045799+00:00 [check:coverage] ----------------------------------------------------------------------------------------------------
2026-10-08T23:09:01.045811+00:00 [check:coverage] src/agent_orchestration_poc/__init__.py                                0      0      0      0   100%
2026-10-08T23:09:01.045832+00:00 [check:coverage] src/agent_orchestration_poc/core/__init__.py                           0      0      0      0   100%
2026-10-08T23:09:01.045852+00:00 [check:coverage] src/agent_orchestration_poc/core/analysis/__init__.py                  0      0      0      0   100%
2026-10-08T23:09:01.045859+00:00 [check:coverage] src/agent_orchestration_poc/core/analysis/notebooks.py                54      0     26      0   100%
2026-10-08T23:09:01.045866+00:00 [check:coverage] src/agent_orchestration_poc/core/analysis/transcript_retro.py        202      5     96      9    95%
2026-10-08T23:09:01.045873+00:00 [check:coverage] src/agent_orchestration_poc/core/coordinator_preflight.py             47      0     18      1    98%
2026-10-08T23:09:01.045880+00:00 [check:coverage] src/agent_orchestration_poc/core/coverage_floors.py                   44      0     14      2    97%
2026-10-08T23:09:01.045887+00:00 [check:coverage] src/agent_orchestration_poc/core/gate_changes.py                     278      3    132      3    99%
2026-10-08T23:09:01.045894+00:00 [check:coverage] src/agent_orchestration_poc/core/gremlins_output.py                    7      0      0      0   100%
2026-10-08T23:09:01.045901+00:00 [check:coverage] src/agent_orchestration_poc/core/host_socket_attribution.py          170      0     74      0   100%
2026-10-08T23:09:01.045907+00:00 [check:coverage] src/agent_orchestration_poc/core/mutation_score.py                    13      0      6      0   100%
2026-10-08T23:09:01.045914+00:00 [check:coverage] src/agent_orchestration_poc/core/operator_commands.py                131      4     72      4    96%
2026-10-08T23:09:01.045921+00:00 [check:coverage] src/agent_orchestration_poc/core/parent_link_sync.py                 127      2     62      2    98%
2026-10-08T23:09:01.045928+00:00 [check:coverage] src/agent_orchestration_poc/core/pr_size.py                           70      0     22      0   100%
2026-10-08T23:09:01.045950+00:00 [check:coverage] src/agent_orchestration_poc/core/project_rank.py                      99      1     30      1    98%
2026-10-08T23:09:01.045976+00:00 [check:coverage] src/agent_orchestration_poc/core/review_identity.py                   20      0      2      0   100%
2026-10-08T23:09:01.045983+00:00 [check:coverage] src/agent_orchestration_poc/core/skipscan.py                         272      4    138      5    98%
2026-10-08T23:09:01.045989+00:00 [check:coverage] src/agent_orchestration_poc/core/subject.py                           10      0     10      0   100%
2026-10-08T23:09:01.045993+00:00 [check:coverage] src/agent_orchestration_poc/core/work_model_backfill.py              483     21    224     18    94%
2026-10-08T23:09:01.045998+00:00 [check:coverage] src/agent_orchestration_poc/core/work_model_backfill_executor.py     728     28    390     29    95%
2026-10-08T23:09:01.046002+00:00 [check:coverage] src/agent_orchestration_poc/core/work_model_backfill_rollback.py     131      4     70      4    96%
2026-10-08T23:09:01.046006+00:00 [check:coverage] src/agent_orchestration_poc/core/workflow_forms.py                   186      0     74      0   100%
2026-10-08T23:09:01.046010+00:00 [check:coverage] src/agent_orchestration_poc/shell/__init__.py                          0      0      0      0   100%
2026-10-08T23:09:01.046014+00:00 [check:coverage] src/agent_orchestration_poc/shell/analysis/__init__.py                 0      0      0      0   100%
2026-10-08T23:09:01.046018+00:00 [check:coverage] src/agent_orchestration_poc/shell/analysis/notebooks.py               74      2     30      3    95%
2026-10-08T23:09:01.046022+00:00 [check:coverage] src/agent_orchestration_poc/shell/analysis/transcript_retro.py        14      0      6      1    95%
2026-10-08T23:09:01.046026+00:00 [check:coverage] src/agent_orchestration_poc/shell/coordinator_preflight.py           108     26     28      7    71%
2026-10-08T23:09:01.046030+00:00 [check:coverage] src/agent_orchestration_poc/shell/gate_changes.py                     54      8     18      4    78%
2026-10-08T23:09:01.046034+00:00 [check:coverage] src/agent_orchestration_poc/shell/go_branch_coverage.py               20      0      4      0   100%
2026-10-08T23:09:01.046051+00:00 [check:coverage] src/agent_orchestration_poc/shell/operator_commands.py                76     13     26      6    79%
2026-10-08T23:09:01.046087+00:00 [check:coverage] src/agent_orchestration_poc/shell/parent_link_sync.py                148     45     54     10    62%
2026-10-08T23:09:01.046096+00:00 [check:coverage] src/agent_orchestration_poc/shell/pr_size.py                          77      5     16      4    90%
2026-10-08T23:09:01.046100+00:00 [check:coverage] src/agent_orchestration_poc/shell/project_rank.py                    166     22     56     16    83%
2026-10-08T23:09:01.046104+00:00 [check:coverage] src/agent_orchestration_poc/shell/review_identity.py                  30      5      8      2    82%
2026-10-08T23:09:01.046108+00:00 [check:coverage] src/agent_orchestration_poc/shell/skipscan.py                         83     18     26      6    78%
2026-10-08T23:09:01.046112+00:00 [check:coverage] src/agent_orchestration_poc/shell/work_model_backfill.py             460    175    156     24    58%
2026-10-08T23:09:01.046116+00:00 [check:coverage] src/agent_orchestration_poc/shell/workflow_forms.py                  122     11     44      6    90%
2026-10-08T23:09:01.046120+00:00 [check:coverage] src/agent_orchestration_poc/shell/workflow_new_issue.py               27      0      8      1    97%
2026-10-08T23:09:01.046124+00:00 [check:coverage] ----------------------------------------------------------------------------------------------------
2026-10-08T23:09:01.046128+00:00 [check:coverage] TOTAL                                                               4531    402   1940    168    90%
2026-10-08T23:09:01.046142+00:00 [check:coverage] Coverage JSON written to file .coverage-reports/python.json
2026-10-08T23:09:01.046166+00:00 [check:coverage] ============================ 1224 passed in 58.08s =============================
2026-10-08T23:09:01.168397+00:00 [check:coverage] $ go test -tags=integration -coverprofile=.coverage-reports/go…
2026-10-08T23:09:01.656998+00:00 [check:coverage] 	github.com/tbhb/agent-orchestration-poc/cmd/agentctl		coverage: 0.0% of statements
2026-10-08T23:09:01.657027+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/cmd/agentd	(cached)	coverage: 60.7% of statements
2026-10-08T23:09:01.657038+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/api	[no test files]
2026-10-08T23:09:01.657047+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/backend/container	[no test files]
2026-10-08T23:09:01.657065+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/backend/tmux	[no test files]
2026-10-08T23:09:01.657073+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/bus	(cached)	coverage: 75.6% of statements
2026-10-08T23:09:01.657081+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/cli	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.657089+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/core	[no test files]
2026-10-08T23:09:01.657096+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/command	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.657103+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/layout	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.657110+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/perms	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.657116+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/relay	(cached)	coverage: 92.3% of statements
2026-10-08T23:09:01.657123+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/core/subject	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.657129+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/registry	[no test files]
2026-10-08T23:09:01.657148+00:00 [check:coverage] ?   	github.com/tbhb/agent-orchestration-poc/internal/term	[no test files]
2026-10-08T23:09:01.657155+00:00 [check:coverage] ok  	github.com/tbhb/agent-orchestration-poc/internal/version	(cached)	coverage: 100.0% of statements
2026-10-08T23:09:01.689837+00:00 [check:coverage] $ uv run python scripts/check-coverage.py
2026-10-08T23:09:01.813986+00:00 [check:coverage] Python core lines: 97.66% (floor 95%)
2026-10-08T23:09:01.814022+00:00 [check:coverage] Python core branches: 94.38% (floor 90%)
2026-10-08T23:09:01.814033+00:00 [check:coverage] Python shell lines: 77.38% (floor 70%)
2026-10-08T23:09:01.814042+00:00 [check:coverage] Go core statements: 96.43% (floor 95%)
2026-10-08T23:09:01.814050+00:00 [check:coverage] Go shell statements: 74.58% (floor 70%)
2026-10-08T23:09:01.814066+00:00 [check:coverage] Go branch coverage: internal/core
2026-10-08T23:09:02.415987+00:00 [check:coverage] Go branch coverage: internal/core/command
2026-10-08T23:09:03.717782+00:00 [check:coverage] Go branch coverage: internal/core/layout
2026-10-08T23:09:05.430012+00:00 [check:coverage] Go branch coverage: internal/core/perms
2026-10-08T23:09:06.690801+00:00 [check:coverage] Go branch coverage: internal/core/relay
2026-10-08T23:09:08.064163+00:00 [check:coverage] Go branch coverage: internal/core/subject
2026-10-08T23:09:09.280022+00:00 [check:coverage] Go core branches: 94.74% (floor 90%)
2026-10-08T23:09:09.292251+00:00 Finished in 67.89s
2026-10-08T23:09:09.295967+00:00 exit 0
```

## Other validation

Verified: `mise run vale:sync`, `mise run fmt`, and `mise run build` passed. Formatters made no source changes. Integration checks regenerated two existing chart artifacts, which were restored after verification.

Verified: `mise run pr:size -- origin/main` reports 127 counted units, comprising 55 task-configuration units, 60 test units, and 12 documentation units. This report is excluded evidence.

Verified: gate comparison requires `gate:selector:mise.toml:file:changed`. The PR body supplies the reason that the wrappers retain all original commands and dependencies, without narrowing gates. The check passed with:

```sh
mise run check:gate-changes -- --base 0e579b7 --head HEAD --body-file /tmp/check-semaphore-332-pr.md
```

## Blocking sandbox result

Observed: `CHECK_LINKS=1 mise run docs:build` acquired the semaphore and ran dependency installation and Astro. It exited 1 because Chromium could not register its Mach rendezvous server inside the sandbox:

```text
FATAL:base/apple/mach_port_rendezvous_mac.cc:159
bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.46196: Permission denied (1100)
```

The missing rendered pages then caused seven link-validation errors. Rendering and link validation were not disabled. The repository's no-arbitrary-skipping rule requires stopping at this blocked check. The operator must run the same command outside this worker sandbox, then resume the worker with the result:

```sh
cd /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-332-check-semaphore
CHECK_LINKS=1 mise run docs:build
```

Observed: `mise run check:mutation` acquired a lease and entered the nested Go mutation task without a descriptor-inheritance error. It was interrupted with Ctrl-C, exit 130, when work stopped at the docs sandbox block. Mutation scores and nested Python execution remain unverified. A fresh full mutation run is required after resumption.

The sandbox also denied `ps` during cleanup. Sending Ctrl-C through the existing command session succeeded. No process-inspection workaround was used.

No PR was opened during this blocked run. The implementation commit `03808c84a2b2ef59aaed48ab528a134653d6d1ea` was already pushed before this run began.

## Checks completed outside the Codex sandbox

Harness: Claude Code, model `claude-opus-5-5`. Same worktree at `03808c8`, run outside the Codex sandbox, one check at a time, each through the installed semaphore as `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/check-semaphore -- <cmd>`. Times are UTC.

| Command | Start | End | Exit | Result |
| --- | --- | --- | --- | --- |
| `mise run check` | 2026-10-08T23:14:39Z | 2026-10-08T23:15:59Z | 0 | `check:pytest` 1,063 passed, 161 skipped; `check:coverage` 1,224 passed, including the 20 wrapper fixtures; all coverage floors met |
| `CHECK_LINKS=1 mise run docs:build` | 2026-10-08T23:16:20Z | 2026-10-08T23:16:36Z | 0 | 62 pages built; "All internal links are valid." |
| `mise run check:mutation` | 2026-10-08T23:17:37Z | 2026-10-08T23:25:09Z | 0 | Go: 149 mutants classified, test efficacy 97.32%, mutator coverage 100.00%; Python core mutation score 90.11% (11,854 killed of 13,155) |

Observed: the `check` run's integration tests again regenerated the two example chart SVGs under `research/gates/data-analysis/` and added a Quarto `.gitignore` there. Those were restored and removed before committing.

Verified: nested leases for both Go and Python. The outer semaphore (wrapper PID 62983) ran `mise run check:mutation`, whose wrapper invoked the semaphore again, then `mise run check:mutation:go` and `mise run check:mutation:python`, each also wrapped. The mutation log shows every wrapper and hidden task in order with no semaphore error. A collector read `queue.json` from the default semaphore directory every 15 seconds. All 29 snapshots after admission show one entry, PID 62983 in slot 0: 7 snapshots during `_check:mutation:go` and 22 during `_check:mutation:python`. The nested wrappers therefore reused the inherited lease rather than queuing for a second slot. Observed: load5 was 10.01 at the start, below the README's load5 condition of 20 for starting mutation. During `_check:mutation:python` it rose to a peak of 26.93 at 23:24:39Z, with load1 peaking at 49.19 at 23:23:54Z. These figures are host-wide; the run does not attribute the load between this job and other processes, and the semaphore does not bound load from them.

First Go and first Python snapshots:

```text
2026-10-08T23:17:52Z load={ 8.61 9.85 12.41 } task=[_check:mutation:go] queue=[{"ID":"cbe484f9-7d3f-479a-b18c-b3c8ce5ec4c6","PID":62983,"Name":"mise","Slot":0,"Alive":true}]
2026-10-08T23:19:37Z load={ 12.96 10.46 12.32 } task=[_check:mutation:python] queue=[{"ID":"cbe484f9-7d3f-479a-b18c-b3c8ce5ec4c6","PID":62983,"Name":"mise","Slot":0,"Alive":true}]
```
