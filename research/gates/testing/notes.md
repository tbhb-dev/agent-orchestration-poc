# Property and mutation testing research gate: raw notes

Recorded 2026-09-26 for the research halves of issue #59 (property-based testing) and issue #60 (mutation testing with a score gate). Both are operator requirements from 2026-09-26, and issue #58 (functional core, imperative shell) sets the target: the pure core takes both kinds of test, and the shell is out of scope for mutation scoring. Every claim carries an evidence label from the standing rules (verified, observed, help-text, schema, documented, inference, untested) and either a clone path at the SHA recorded in `versions.md` or a command with its output. Codex writes the conventions pages and rules from these notes; this file is neither.

Tools ran through mise from the worktree: `mise exec -- go version` printed `go version go1.27.1 darwin/arm64`, `mise exec -- python --version` printed `Python 3.14.6`, and `mise exec -- uv --version` printed `uv 0.12.10`. Trials ran in throwaway modules under a `mktemp -d` directory outside the repository, with `GOTOOLCHAIN=local` and `UV_PYTHON_PREFERENCE=only-system` as `mise.toml` sets them. The Python scratch project copied this repository's `[tool.pytest.ini_options]` table and `tests/conftest.py` unchanged, so the pytest results below are results under the adopted configuration.

Clone shorthand: `rapid` is `~/Code/github.com/flyingmutant/rapid`, `gopter` is `~/Code/github.com/leanovate/gopter`, `hypothesis` is `~/Code/github.com/HypothesisWorks/hypothesis`, `gremlins` is `~/Code/github.com/go-gremlins/gremlins`, `go-mutesting` is `~/Code/github.com/zimmski/go-mutesting`, `mutmut` is `~/Code/github.com/boxed/mutmut`, and `cosmic-ray` is `~/Code/github.com/sixty-north/cosmic-ray`, each at the SHA in `versions.md`.

The issues name `research/gates/property-testing/` and `research/gates/mutation-testing/` as the notes directories. The coordinator's work item put both in `research/gates/testing/`, so this file covers both and the issues' acceptance criteria need that path read in.

## 1. Property testing for Go

### Recommendation

Adopt `pgregory.net/rapid` v1.3.0. Reject `github.com/leanovate/gopter` v0.2.11.

### Go 1.27 support

- Observed: a scratch module with `go 1.27.0` took `pgregory.net/rapid v1.3.0` and `github.com/leanovate/gopter v0.2.11` through `go get`, and `mise exec -- go test -race -shuffle=on -v ./...` passed for both under go1.27.1 (`ok example.com/goprop/subject 1.335s`, 4.6 s wall clock with compilation).
- Verified: rapid declares `go 1.23` in `go.mod` at HEAD and at tag `v1.3.0`, and its workflow tests Go 1.23, 1.24, 1.25, and 1.26 (`rapid/go.mod`; `rapid/.github/workflows/ci.yml` line 12). Go 1.27 is not in its matrix, so 1.27 support is observed here, not claimed upstream.
- Verified: gopter declares `go 1.20` and its workflow tests Go 1.20, 1.21, and 1.22 only (`gopter/go.mod`; `gopter/.github/workflows/build.yml` line 7).
- Verified: rapid has `testing/synctest` support for Go 1.25 and later through `rapid.SyncTest` (`rapid/synctest_enabled.go` lines 10 to 26; commit `b9c78bf`), which matches the Go rule that internal time logic uses `synctest.Test`. Untested here.

### Generator API

- Verified: rapid generators are generic and typed, `*Generator[V]`, with `Custom`, `Map`, `Filter`, `Just`, `OneOf`, `SampledFrom`, `Permutation`, `Deferred`, `Ptr`, `SliceOf`, `SliceOfN`, `SliceOfDistinct`, `MapOf`, `MapOfN`, `String`, `StringN`, `StringOf`, `StringMatching`, `RuneFrom`, the sized integer and float families, and `Make[V]` for reflection-derived values (`rapid/combinators.go`, `collections.go`, `strings.go`, `integers.go`, `floats.go`, `make.go`). Values come from `gen.Draw(t, "label")` inside the property, so a property is ordinary imperative Go.
- Verified: gopter predates generics. `prop.ForAll(condition interface{}, gens ...gopter.Gen)` checks the condition function by reflection, `Gen.Map(f interface{})` takes an untyped function, and `gen.Struct` takes a `reflect.Type` and a map of field names (`gopter/prop/forall.go` lines 21 to 27; `gopter/gen.go` line 109; `gopter/gen/struct.go` line 14). A wrong argument type is a run-time error, not a compile error.
- Inference: the bus and registry shapes are subject strings, token lists, identifiers, and small structs of those. rapid covers them with `StringMatching`, `SliceOfN`, `MapOf`, and `Custom` without reflection. rapid also has a state machine API (`rapid/statemachine.go`) for the registry's add, remove, and lookup sequences. Untested here.

### Shrinking

- Observed: on a deliberately false property over strings from the alphabet `ab.*>`, rapid reported the minimal counterexample: `[rapid] failed after 2 tests: Valid(".") = false` with `[rapid] draw s: "."`.
- Observed: gopter on the same property, with the string built through `gen.SliceOfN(8, ...).Map(...)`, reported the unshrunk `ARG_0: >*a>b*b.`.
- Documented: that is gopter's stated behavior, "The derived generator will not have a sieve or shrinker unless you are mapping to the same type" (`gopter/gen.go` lines 104 to 108). Keeping shrinking through a type change needs a hand-written `gopter.DeriveGen` bi-directional mapping (`gopter/CHANGELOG.md`, Unreleased section).
- Verified: rapid shrinks the recorded bit stream, not the value, so every generator built from combinators shrinks with no shrinker code (`rapid/shrink.go`; `rapid/data.go` `recordedBits`). `-rapid.shrinktime` bounds the time spent (`rapid/engine.go` line 75).

### Integration with `testing` and `t.Run`

- Verified: `rapid.Check(t, func(*rapid.T))` runs inside a normal `TestXxx`, and `rapid.MakeCheck(prop)` returns a `func(*testing.T)` made for `t.Run("name", ...)` (`rapid/engine.go` lines 205 to 229). That fits the adopted rule of named subtests with `t.Run`.
- Observed: `go test -v` lists each property as a subtest, `--- PASS: TestValidRapid/join_of_plain_tokens_is_valid (0.01s)`, with `[rapid] OK, passed 100 tests (5.174875ms)`.
- Verified: gopter collects properties in a `gopter.Properties` value and runs them all in `TestingRun(t)`, which reports through its own console reporter and one `t.Errorf` (`gopter/properties.go` lines 47 to 59). Properties are not subtests, so `-run` cannot select one.
- Verified: `rapid.MakeFuzz(prop)` turns the same property into a `testing.F` fuzz target (`rapid/engine.go` line 238). Untested here.
- Observed: `mise exec golangci-lint@2.14.0 -- golangci-lint run ./...` with this repository's `.golangci.yml` raised nothing on the rapid and gopter test files. Its one finding, `QF1002`, was on the scratch validator's own `switch`.

### Determinism and seeds for CI

- Verified: rapid defaults to 100 checks per property and a random seed, `new(maphash.Hash).Sum64()`, unless `-rapid.seed` is non-zero (`rapid/engine.go` lines 66 to 81; `rapid/data.go` lines 21 to 27). `go test -short` divides the check count by five (`rapid/engine.go` lines 274 to 277).
- Verified: every `-rapid.` flag has a `RAPID_` environment variable that sets its default, including `RAPID_SEED`, `RAPID_CHECKS`, and `RAPID_NOFAILFILE` (`rapid/engine.go` lines 89 to 98; `rapid/README.md` lines 192 to 196).
- Observed: a failure prints its seed, `To reproduce, specify -run="TestShrinkRapid" -rapid.seed=8642669569915471698`. Two reruns with that flag and one with `RAPID_SEED=8642669569915471698` each printed the same `failed after 0 tests: Valid(".") = false`. `RAPID_CHECKS=1000` printed `[rapid] OK, passed 1000 tests (1.065541ms)`.
- Observed: a failure also writes a fail file, `testdata/rapid/TestShrinkRapid/TestShrinkRapid-20260926180148-13976.fail`, in the package directory. Verified: later runs replay every fail file found for the test before generating new cases (`rapid/engine.go` lines 329 to 342; `rapid/persist.go` lines 55 to 60).
- Verified: gopter seeds from `time.Now().UnixNano()` and prints `failed with initial seed: N`, and reproducing means editing the test to call `gopter.DefaultTestParametersWithSeed(N)` (`gopter/test_parameters.go` lines 32 to 48; `gopter/properties.go` line 57). There is no flag or environment variable.
- Inference: for the pull request gate, set `RAPID_SEED` to a fixed non-zero value and `RAPID_NOFAILFILE=1` in the CI workflow environment, and leave both unset locally. CI then runs the same cases on every run, which matches what Hypothesis does on CI by default (section 2), and local runs keep exploring. The alternative is random seeds in CI as well, which finds more and can fail a pull request on a bug the change did not introduce. This is the coordinator's call.
- Inference: a fail file is a reproduction aid, not a regression suite, because its format is tied to a rapid version marker (`rapid/persist.go` line 21). Turn a found counterexample into a named table case and delete the fail file rather than committing it.

### Maintenance

- Verified: rapid's last commit is 2026-09-04 and tag `v1.3.0` is 2026-03-30. Its README states "Rapid is stable: tests using rapid should continue to work with all future rapid releases with the same major version" (`rapid/README.md`, Status). It has no dependencies outside the standard library (`rapid/go.mod`).
- Verified: gopter's last tag `v0.2.11` is 2024-04-03, and eight commits follow it, the last on 2026-04-20, a merged range-shrinker fix. Its changelog's Unreleased section has never been cut into a release entry (`gopter/CHANGELOG.md` line 3).

### Example test

Observed passing under go1.27.1 with `-race -shuffle=on`. The function under test is a pure subject-name validator.

```go
func TestValidRapid(t *testing.T) {
	token := rapid.StringMatching(`^[A-Za-z0-9_-]{1,8}$`)
	t.Run("join of plain tokens is valid", rapid.MakeCheck(func(t *rapid.T) {
		tokens := rapid.SliceOfN(token, 1, 6).Draw(t, "tokens")
		if !subject.Valid(subject.Join(tokens)) {
			t.Fatalf("Valid(%q) = false, want true", subject.Join(tokens))
		}
	}))
}
```

### Pinning

- Inference: rapid is a test dependency of the module, so it pins through `go.mod` and `go.sum` with `go get pgregory.net/rapid@v1.3.0`, not through mise. It will be the module's first `require`, so `go mod tidy -diff` and `go mod verify` in `check:go` start covering a real dependency.

## 2. Property testing for Python

### Recommendation

Adopt `hypothesis` 6.168.1 in the `dev` dependency group. It is the only candidate the issue names.

### Python 3.14 support

- Verified: `requires-python = ">= 3.10"` with a `Programming Language :: Python :: 3.14` classifier (`hypothesis/hypothesis/pyproject.toml` lines 18 and 35). Upstream CI runs its main jobs on 3.14 and pins 3.14.7 in its tooling (`hypothesis/.github/workflows/main.yml` lines 39 and 131; `hypothesis/tooling/src/hypothesistooling/__main__.py` line 839).
- Documented: the changelog lists "Python versions: 3.10, 3.11, 3.12, 3.13, 3.14, 3.14t" for its wheels and records 3.14 fixes and Python 3.15 support (`hypothesis/hypothesis/docs/changelog.rst` lines 147, 576, 1456, 1692, 1716).
- Observed: `mise exec -- uv add --dev hypothesis mutmut cosmic-ray` resolved `hypothesis==6.168.1` on Python 3.14.6, and `import hypothesis` printed `6.168.1 3.14.6`.
- Documented: since 6.156.0 (2026-07-01) Hypothesis is moving internals to Rust and "now requires a rust toolchain to build from source (if not installing from a native wheel)" (`changelog.rst` lines 570 to 572). The build backend is maturin (`pyproject.toml` lines 1 to 3).
- Observed: uv installed a wheel, and the extension loaded as `_native.cpython-314-darwin.so`. PyPI lists 84 wheels and one sdist for 6.168.1. Inference: macOS arm64 and the Linux x86-64 CI runner both get wheels, so the pinned Rust toolchain in `mise.toml` is not needed for it. The Linux install is untested here.

### Pytest integration

- Verified: Hypothesis ships a pytest plugin through the `pytest11` entry point, so installing it is enough (`pyproject.toml` lines 134 to 135). The plugin adds `--hypothesis-profile`, `--hypothesis-verbosity`, `--hypothesis-show-statistics`, `--hypothesis-seed`, and `--hypothesis-explain` (`hypothesis/hypothesis/src/_hypothesis_pytestplugin.py` lines 38 to 42).
- Observed: the run header names the active profile, `hypothesis profile 'default'`, and `--hypothesis-seed=1` ran (`2 passed in 0.79s`).
- Observed: on a false property the failure shrank to `s='.'`, the rerun replayed it from the database (`during reuse phase (0.01 seconds)` in `--hypothesis-show-statistics`), and with `print_blob=True` the report added `@reproduce_failure('6.168.1', b'AII+Pg==')`.

### Interaction with the adopted pytest configuration

- Observed: with this repository's table copied verbatim (`addopts = "-ra --import-mode=importlib"`, `filterwarnings = ["error"]`, `strict_config`, `strict_markers`, `strict_xfail`, `minversion = "9.1"`, `testpaths = ["tests"]`) and its `tests/conftest.py`, `mise exec -- uv run pytest -q` printed `9 passed in 1.24s`: two properties at 100 examples each and seven parametrized cases. No warning was raised, so `filterwarnings = error` needs no exception for Hypothesis.
- Verified: the plugin registers the `hypothesis` marker itself in `pytest_configure` (`_hypothesis_pytestplugin.py` lines 155 to 156), which is why `strict_markers` passes with no entry in `markers`.
- Observed: `--import-mode=importlib` with `tests/` lacking `__init__.py` works. The property test imports only the installed package and `hypothesis`.
- Inference: `filterwarnings = error` turns `HypothesisDeprecationWarning` and `NonInteractiveExampleWarning` into failures. That is the wanted behavior: a deprecated strategy argument or a stray `.example()` call in a test fails `check`. Untested here.
- Observed: `uv run ruff check` with this repository's ruff configuration rejects `from hypothesis import given, strategies as st` under `I001` and rewrites it as two imports. `ruff format --check` passed.

### Settings profile for CI

- Verified: defaults are `max_examples=100`, `derandomize=False`, and a 200 ms per-example `deadline` (`hypothesis/hypothesis/src/hypothesis/_settings.py` lines 630 and 1210 to 1220).
- Verified: Hypothesis registers a built-in `ci` profile, `derandomize=True`, `deadline=None`, `database=None`, `print_blob=True`, `suppress_health_check=[HealthCheck.too_slow]`, and loads it at import when `is_in_ci()` sees `CI` or another known variable set (`_settings.py` lines 392 to 413 and 1227 to 1238). GitHub Actions sets `CI`.
- Verified: `derandomize=True` seeds from "a hash of the test function, so that every run will test the same set of test cases until you update Hypothesis, Python, or the test function", and "If running on CI, the default is True" (`_settings.py` lines 797 to 810). It also forces `database=None`, and passing both raises `InvalidArgument` (`_settings.py` lines 684 to 690).
- Observed: with `CI=true` and a `ci` profile registered in `conftest.py`, the header read `hypothesis profile 'ci' -> database=None, deadline=None, print_blob=True, max_examples=200, derandomize=True, suppress_health_check=(HealthCheck.too_slow,)`. Registering a profile under the name `ci` replaces the built-in one, and it took effect with no `load_profile` call because it was already the active profile. With `CI` unset the header read `hypothesis profile 'default'`.
- Documented: `conftest.py` is the standard place to register profiles, and `--hypothesis-profile` or an environment variable read in `conftest.py` selects one (`hypothesis/hypothesis/docs/tutorial/settings.rst` lines 60 to 110).
- Inference: keep the built-in `ci` profile and register nothing. It is deterministic, has no deadline, so a slow shared runner cannot fail a test on timing, and writes no database. Add profiles to `tests/conftest.py` only when a need appears, for example a `thorough` profile with `max_examples=1000` for a scheduled run.
- Inference: the 200 ms deadline stays on locally under the `default` profile. Pure core functions should be far under it. A test that trips it is either doing I/O, which issue #58 forbids in the core, or needs `@settings(deadline=None)` with a reason.

### Database handling in the repository

- Observed: a local run creates `.hypothesis/` at the project root with `constants`, `unicode_data`, and, after a failure, `examples` and `patches`. Hypothesis writes `.hypothesis/.gitignore` containing `*`, with a comment that it "gitignores .hypothesis by default, because we generally recommend that .hypothesis not be checked into version control".
- Observed: with `CI=true` no `examples` directory appeared after a failing run, which confirms `database=None` under the `ci` profile.
- Documented: sharing the directory database through version control "only makes sense if you also pin to an exact version of Hypothesis" and upstream recommends a network datastore over it (`hypothesis/hypothesis/src/hypothesis/database.py` lines 423 to 438).
- Inference: commit nothing and add nothing to `.gitignore`, because the directory ignores itself. `.hypothesis/` sits at each worktree's root, so parallel agent worktrees do not share or contend on a database. The pre-commit gitleaks and whitespace hooks never see it.

### Example test

Observed passing under Python 3.14.6 and the adopted pytest configuration, and clean under `ruff check` in this import form.

```python
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.subject import join, valid

token = st.from_regex(r"\A[A-Za-z0-9_-]{1,8}\Z")


@given(st.lists(token, min_size=1, max_size=6))
def test_join_of_plain_tokens_is_valid(tokens):
    assert valid(join(tokens))
```

### Pinning

- Inference: `mise exec -- uv add --dev 'hypothesis>=6.168.1'` follows the existing `dev` group form (`pytest>=9.1.1`), and `uv.lock` holds the exact version. uv 0.12.10 has no `uv pip index versions` subcommand (`error: unrecognized subcommand 'index'`), so versions here come from the PyPI JSON API and from what `uv add` resolved.

## 3. Mutation testing for Go

### Recommendation

Adopt gremlins v0.6.0, pinned in mise through the `go:` backend. Reject go-mutesting, which does not run under Go 1.27.1.

### Go 1.27 support

- Observed: `mise exec -- env GOBIN=<scratch>/bin go install github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0` built under go1.27.1 in 2.6 s, and the binary ran every trial below. Without the explicit `GOBIN`, mise's own `GOBIN` sent the binary to `~/.local/share/mise/installs/go/1.27.1/bin/`. That stray copy from the first attempt was deleted. `gremlins --version` prints `gremlins version dev darwin/arm64` for a `go install` build, so the binary cannot confirm its own version.
- Verified: gremlins declares `go 1.25` at tag `v0.6.0` and `go 1.25.0` at HEAD, and its workflows take the Go version from `go.mod` (`gremlins/go.mod`; `gremlins/.github/workflows/ci.yml` line 17). Go 1.27 support is observed here, not claimed upstream.
- Observed: go-mutesting installed with `go install ...@latest` under go1.27.1 and then failed on the scratch core package, by directory and by import path: `The following panic happened checking types near: .../go/1.27.1/src/internal/coverage/rtcov/rtcov.go:19:6` and `panic: runtime error: invalid memory address or nil pointer dereference`. The stack is inside `golang.org/x/tools@v0.0.0-20191018212557-ed542cd5b28a/go/packages`.
- Verified: go-mutesting declares `go 1.10`, requires that 2019 `golang.org/x/tools`, and has had no commit since 2021-06-10 (`go-mutesting/go.mod`; `git log`). Its only tag, `v1.2`, is not a valid module version, so Go resolves the pseudo-version `v0.0.0-20210610104036-6d9217011a00`.

### Mutation operators

- Documented: gremlins has eleven mutant types. Five are on by default: arithmetic base, conditionals boundary, conditionals negation, increment decrement, and invert negatives. Six are off by default: invert logical, invert loop control, invert assignments, invert bitwise, invert bitwise assignments, and remove self assignments (`gremlins/docs/docs/usage/mutations/index.md`). Each has a flag and a `mutants.<name>.enabled` configuration key (`gremlins/docs/docs/usage/configuration.md` lines 45 to 86).
- Documented: go-mutesting has six mutators: `branch/case`, `branch/if`, `branch/else`, `expression/comparison`, `expression/remove`, and `statement/remove` (`go-mutesting/README.md` lines 222 to 243).
- Inference: start with the gremlins defaults. `invert-logical` and `invert-loopctrl` are the two worth adding for validation and routing logic once the first real score exists. Untested here.

### Package scoping

- Verified: `gremlins unleash [path]` takes at most one path, finds the module root from it, and runs coverage and mutation over `./<path>/...` (`gremlins/cmd/unleash.go` lines 70 to 111; `gremlins/internal/coverage/coverage.go` lines 167 to 171).
- Observed: `gremlins unleash ./internal/core` mutated only `internal/core`, while a bare `gremlins unleash` from the module root also listed `internal/shell/shell.go`.
- Observed: `exclude-files` regular expressions match the path relative to the path argument, not the module root. With `gremlins unleash ./internal`, `^internal/shell/` excluded nothing and `^shell/` excluded the shell package. From the module root with no path argument, `internal/shell/` excluded it.
- Documented: an excluded file "is skipped from execution and threshold calculation" (`gremlins/docs/docs/usage/commands/unleash/index.md` line 69).
- Documented: gremlins by default runs only the tests of the package that holds the mutant, and `--integration` runs the whole suite for each mutant at a large cost in time (`unleash/index.md` lines 220 to 235). Inference: the default is right for a pure core, which has its own tests.
- Inference: the scope depends on the layout issue #58 settles. If the core sits under one directory, pass that directory as the path and keep `exclude-files` empty. If core and shell packages are siblings under `internal/`, run from the module root and list the shell packages and `^cmd/` in `exclude-files`. The first form is an allowlist and cannot silently include a new shell package, so prefer it.

### Threshold gate

- Documented: `--threshold-efficacy` exits with code 10 when efficacy, `KILLED / (KILLED + LIVED)`, is under the value. `--threshold-mcover` exits with code 11 when mutant coverage, `(KILLED + LIVED) / (KILLED + LIVED + NOT_COVERED)`, is under the value. Both default to 0, which disables them (`unleash/index.md` lines 389 to 412). The configuration keys are `unleash.threshold.efficacy` and `unleash.threshold.mutant-coverage` (`configuration.md` lines 58 to 60).
- Observed: with `threshold.efficacy: 90` in `.gremlins.yaml` and one table case removed from the test, gremlins printed `LIVED ARITHMETIC_BASE at subject.go:17:23`, `LIVED INVERT_NEGATIVES at subject.go:17:23`, `Killed: 7, Lived: 2, Not covered: 3`, `Test efficacy: 77.78%`, `Mutator coverage: 75.00%`, and `ERROR: below efficacy-threshold`, and exited 10. This is the deliberately surviving mutant issue #60 asks for, on the scratch module. The repository's own first score waits for core code.
- Observed: efficacy alone does not see untested code. Removing the cases that reach a branch moved its mutants from `KILLED` to `NOT COVERED`, and efficacy stayed at `100.00%` while mutator coverage fell to `50.00%`. The gate needs both thresholds.
- Verified: gremlins finds `.gremlins.yaml` in the working directory without a flag, and `--config` overrides it (`gremlins/internal/configuration/configuration.go` lines 54 to 89; `configuration.md` lines 34 to 40). Observed: the threshold above came from the file, with no flag.
- Documented: go-mutesting prints `The mutation score is 0.750000 (6 passed, 2 failed, 0 skipped, total is 8)` and has no threshold option. Its exit codes describe the `--exec` command contract, not a gate (`go-mutesting/README.md` lines 135 to 140 and 211 to 218).

### Proposed threshold

- Inference: efficacy 80 and mutant coverage 80, as a starting floor. The scratch validator scored 100.00% efficacy with full table cases and 77.78% with one case removed, so 80 separates a complete table from a thin one on code of that kind. Raise the floor after the first real score per language, which issue #60 records as evidence. Do not start at 100, because equivalent mutants exist and the only per-mutant exemption gremlins has is excluding a whole file.

### Speed

- Observed: on the scratch core package, 33 lines with twelve mutants, `gremlins unleash ./internal/core` took 2.77 s wall clock: `Gathering coverage... done in 682.82525ms` and `Mutation testing completed in 2 seconds 60 milliseconds`. `--dry-run` took 6 ms.
- Observed: one run at the default timeout coefficient reported `TIMED OUT CONDITIONALS_NEGATION at subject.go:23:35` for a mutant that other runs killed. Documented: the per-mutant timeout is the coverage run's duration times the coefficient, default 5 (`unleash/index.md` lines 413 to 428). With a test run this short the timeout is a few seconds and process start-up noise can exceed it. No run at `timeout-coefficient: 20` timed out.
- Observed: `gremlins unleash --dry-run` on this repository today reports `Runnable: 0, Not covered: 4`, all in `cmd/`. There is no core code yet, so there is no first score yet.

### Output formats

- Documented: `--output <file>` writes JSON with `go_module`, `test_efficacy`, `mutations_coverage`, the counts, and per-file mutations with `type`, `status`, `line`, and `column` (`unleash/index.md` lines 297 to 351). Observed: the file began `{"go_module":"example.com/gomut","files":[{"file_name":"subject.go","mutations":[{"type":"CONDITIONALS_NEGATION","status":"NOT COVERED","line":20,"column":12},`.
- Documented: `--output-statuses` filters the console lines by status letter, for example `lc` for lived and not covered (`unleash/index.md` lines 120 to 167). Observed: it works in v0.6.0.
- Observed: `--output-diff-statuses` fails in v0.6.0 with `ERROR: unknown flag: --output-diff-statuses`. Verified: it arrived in commit `b48a4aa` (2026-03-30), after the tag. The documentation in the clone describes HEAD, so read it against the tag.
- Documented: `--diff <ref>` limits mutation to lines changed against a git ref, for example `origin/$GITHUB_BASE_REF` (`unleash/index.md` lines 83 to 105). Untested here. Inference: useful later to keep the pull request job fast, but the threshold then scores only the changed lines.

### Mise pinning

- Observed: `mise registry` has no entry for gremlins or go-mutesting. `mise ls-remote go:github.com/go-gremlins/gremlins/cmd/gremlins` lists `0.4.0`, `0.5.0`, `0.5.1`, and `0.6.0`. `mise ls-remote go:github.com/zimmski/go-mutesting/cmd/go-mutesting` lists only `0.0.0-20210610104036-6d9217011a00`.
- Inference: pin gremlins the way `guard-markdown` is pinned, through the `go:` backend, which builds it with the pinned Go. Installing it through mise is untested here. The trial binary came from `go install` into a scratch `GOBIN`.

### Proposed configuration and task

`.gremlins.yaml` at the repository root, in the allowlist form. The thresholds and the timeout coefficient are the values observed above.

```yaml
unleash:
  timeout-coefficient: 20
  threshold:
    efficacy: 80
    mutant-coverage: 80
```

`mise.toml` additions. `<core>` is the core directory issue #58 settles on.

```toml
[tools]
"go:github.com/go-gremlins/gremlins/cmd/gremlins" = "0.6.0"

[tasks."check:mutation:go"]
description = "Mutation test the Go core packages with gremlins and fail under the thresholds"
run = "gremlins unleash ./internal/<core> --output-statuses lct"
```

## 4. Mutation testing for Python

### Recommendation

Adopt mutmut 3.8.0 in the `dev` dependency group, with a small script for the score gate. Reject cosmic-ray 8.7.0.

### Python 3.14 support

- Verified: mutmut declares `requires-python = ">=3.10"` with classifiers through 3.15, and its workflow tests 3.10 through 3.15 (`mutmut/pyproject.toml` lines 9 to 24; `mutmut/.github/workflows/tests.yml` line 42). Its history records "Support python 3.14" and, in 3.8.0, "Support python3.15" (`mutmut/HISTORY.rst` lines 33 and 130).
- Verified: cosmic-ray declares `requires-python = ">= 3.9"` with classifiers that stop at 3.13, and its workflow tests 3.9 through 3.13 (`cosmic-ray/pyproject.toml` lines 7 and 20 to 24; `cosmic-ray/.github/workflows/run-tests.yml` line 18). Its changelog has no mention of 3.14.
- Observed: both installed and ran on Python 3.14.6. `cosmic-ray --version` printed `cosmic-ray, version 8.7.0`. For cosmic-ray, 3.14 support is observed here and not claimed upstream.

### Scoping to the core modules

- Verified: mutmut reads `[tool.mutmut]` from `pyproject.toml`. `source_paths` lists what to mutate, and `only_mutate` and `do_not_mutate` take file patterns inside it (`mutmut/src/mutmut/configuration.py` lines 141 to 158; `mutmut/README.rst` lines 140 to 160).
- Observed: `paths_to_mutate` and `tests_dir` still work in 3.8.0 but warn, `The config paths_to_mutate is deprecated. Please rename it to source_paths` and `The config tests_dir is deprecated. Please add the path to pytest_add_cli_args_test_selection instead`. Older guides use the old names.
- Documented: `# pragma: no mutate` exempts a line, `# pragma: no mutate block` a block, and `# pragma: no mutate start` and `end` a range (`README.rst` lines 375 to 480). That is the per-mutant exemption for equivalent mutants, and gremlins has no counterpart.
- Verified: cosmic-ray scopes with `module-path`, a file or a package directory, and `excluded-modules` globs in a TOML file (`cosmic-ray/docs/source/concepts.rst` lines 96 to 140). Exemptions are separate filter programs run on the session between `init` and `exec`: `cr-filter-pragma`, `cr-filter-operators`, `cr-filter-git`, and `cr-filter-lines` (`cosmic-ray/pyproject.toml` lines 52 to 55; `cosmic-ray/docs/source/how-tos/filters.rst` lines 21 to 29).
- Inference: `only_mutate` is the allowlist form and cannot silently include a new shell module, so prefer it once issue #58 names the core modules. Until then `source_paths = ["src/agent_orchestration_poc/"]` covers the whole helper package.

### Threshold gating

- Observed: `mutmut run` exits 0 with surviving mutants. mutmut has no threshold option.
- Verified: `mutmut export-cicd-stats` writes `mutants/mutmut-cicd-stats.json`, and the source comment gives its purpose: "exports CI/CD stats to block pull requests from merging if mutation score is too low" (`mutmut/src/mutmut/__main__.py` lines 701 to 730). Observed: the command name is hyphenated, since `export_cicd_stats` fails with `No such command`, and the file held `{"killed":22,"survived":2,"total":24,"no_tests":0,"skipped":0,"suspicious":0,"timeout":0,"check_was_interrupted_by_user":0,"segfault":0}`.
- Observed: a ten-line script that reads that file and exits 1 under a floor printed `mutation score 95.83% (23 killed of 24)` and returned 0 at a floor of 80 and 1 at a floor of 99. The gate is a script this repository owns, in `scripts/`.
- Verified: cosmic-ray has the gate built in. `cr-rate --fail-over <percent> <session>` exits 1 when the survival rate is over the value (`cosmic-ray/src/cosmic_ray/tools/survival_rate.py` lines 24 to 59). Observed: at a survival rate of 8.51, `--fail-over 20` returned 0 and `--fail-over 5` returned 1. It gates on the survival rate, so an 80% score is `--fail-over 20`.

### Speed

- Observed: mutmut took 4.0 s wall clock for 24 mutants across two files, including generation, the stats run, the clean run, and the forced-fail check, and reported `46.24 mutations/second`.
- Observed: cosmic-ray took 42.7 s wall clock for 47 mutants on the one 24-line module, about 0.9 s each, on two separate runs.
- Verified: the difference is structural. mutmut imports pytest once and forks a child per mutant, and runs only the tests that reach the mutated function (`README.rst` lines 251 to 270; `HISTORY.rst` 3.7.0). cosmic-ray's local distributor rewrites the source file in place and starts the whole `test-command` as a new process for each mutant (`concepts.rst` lines 36 to 40 and 169 to 172).
- Observed: cosmic-ray restored the source file after the run. It still edits the working tree while it runs, which is a hazard in a worktree an agent is editing at the same time.

### Pytest integration with the adopted configuration

- Observed: mutmut copies the sources and tests into `mutants/` and runs pytest there. With this repository's pytest table and `tests/conftest.py` it needed no override: `filterwarnings = error`, `--import-mode=importlib`, and the strict options all held, and the Hypothesis property tests ran as part of the suite.
- Documented: pytest arguments can be added with `pytest_add_cli_args` and `pytest_add_cli_args_test_selection`, for example to deselect the `integration` and `socket` markers (`README.rst` lines 491 to 506). Inference: `tests/conftest.py` already skips those markers without `--run-integration`, so no argument is needed.
- Observed: the one survivor with the full tests was `x_join__mutmut_2`, which changes `".".join(tokens)` to `"XX.XX".join(tokens)`. The property `valid(join(tokens))` still holds for it. The mutation run found a weak property, which is the use of running both kinds of test.
- Observed: all four cosmic-ray survivors were equivalent or near-equivalent mutants, for example `i < len(tokens) - 1` for `i != len(tokens) - 1`, `tok <= ""` for `tok == ""`, and `is not` for `!=`. Its comparison operator replacement produces many of these, so a cosmic-ray score carries more noise for the same tests.
- Observed: mutmut caches results in `mutants/` and did not rerun mutants after a test file changed. The second run printed `0.00 mutations/second` and the same survivors, both after removing a test case and after restoring it. Documented: "Between runs, mutmut only re-tests mutants in functions whose source changed" (`README.rst` line 514). Inference: the task must delete `mutants/` first, or a local score is stale after any test edit. CI starts from a clean checkout either way.
- Inference: `mutants/` needs a `.gitignore` entry. ruff respects `.gitignore` by default and pytest collects only `testpaths`, so neither would pick the copies up. biome, rumdl, and the other tree-wide checks are untested against a populated `mutants/`.

### Proposed threshold

- Inference: a score floor of 80, as a starting floor, the same as Go. The scratch module scored 95.83% with full tests and 91.67% with one table case removed. mutmut's string and argument mutations add survivors gremlins would not generate, and `# pragma: no mutate` with a reason is the answer for an equivalent one. Raise the floor after the first real score.
- Inference: the score is `killed / (killed + survived + timeout + suspicious + no_tests)`. Counting `no_tests` against the score is this script's choice, so that code no test reaches lowers the score, and it does the job of gremlins' mutant coverage threshold with one number.

### Proposed configuration and task

`pyproject.toml` additions.

```toml
[dependency-groups]
dev = ["mutmut>=3.8.0"]

[tool.mutmut]
source_paths = ["src/agent_orchestration_poc/"]
pytest_add_cli_args_test_selection = ["tests/"]
```

`mise.toml` addition. `scripts/check-mutation-score.py` is the gate script described above, and it does not exist yet.

```toml
[tasks."check:mutation:python"]
description = "Mutation test the Python core modules with mutmut and fail under the score floor"
run = [
  "rm -rf mutants",
  "uv run mutmut run",
  "uv run mutmut export-cicd-stats",
  "uv run python scripts/check-mutation-score.py 80",
]
```

## 5. CI shape

### What runs where

- Inference: property tests run in the fast `check` aggregate as ordinary tests, with no new task. rapid properties are `TestXxx` functions that `go test -race -shuffle=on ./...` in `check:go` already runs, and Hypothesis properties are test functions that `uv run pytest` in `check:pytest` already collects.
- Inference: mutation testing runs outside `check`, as `check:mutation` depending on `check:mutation:go` and `check:mutation:python`, which issue #60 already requires.
- Inference: a separate workflow, `mutation.yml`, runs on `pull_request` with a `paths` filter. The Go job triggers on the core package directories, `go.mod`, `go.sum`, and `.gremlins.yaml`. The Python job triggers on `src/agent_orchestration_poc/**`, `tests/**`, `pyproject.toml`, and `uv.lock`. Test files are in the filter because deleting an assertion changes the score without touching the core.
- Inference: make the two languages separate jobs, so a Python change does not pay for the Go run. Give each `timeout-minutes: 15`.
- Inference: a workflow with a `paths` filter that does not run reports no status, so it cannot be a required status check under branch protection as it stands. Either leave it advisory, or have the workflow always run and skip the mutation step when no core path changed. The coordinator manages branch protection, so this is the coordinator's call.
- Inference: set `RAPID_SEED` and `RAPID_NOFAILFILE=1` in the `check.yml` environment if the coordinator takes the deterministic option from section 1. Hypothesis needs nothing, because GitHub Actions sets `CI`.

### Run time estimates

Every number in this table is an inference from the scratch measurements above, scaled to a guessed size. The repository has no core code today: 92 lines of Go under `cmd/` and `internal/`, and 46 lines of Python under `src/` and `tests/`.

| Item | Measured on scratch | Assumed size | Estimate on a GitHub-hosted Linux runner |
| --- | --- | --- | --- |
| rapid properties in `check:go` | 1.5 ms to 5.2 ms for 100 checks | 30 properties | under 1 s added, plus `-race` overhead |
| Hypothesis properties in `check:pytest` | 0.19 s to 1.0 s for two properties | 30 properties at 100 examples | 5 s to 15 s added |
| gremlins on the Go core | 12 mutants in 2.8 s, about 0.2 s each | 1,500 to 3,000 lines, 300 to 700 mutants | 3 to 8 minutes |
| mutmut on the Python core | 24 mutants in 4.0 s | 300 to 600 lines, 150 to 400 mutants | 1 to 2 minutes |

- Inference: the Go estimate has the widest error. Each gremlins mutant rebuilds and runs the package's tests, so the cost per mutant grows with the package's test time, and the scratch package's tests run in milliseconds. Hosted runners also have fewer cores than the machine these trials ran on, and gremlins defaults its workers to the CPU count (`configuration.md` line 89).
- Inference: if the Go job passes ten minutes, `--diff origin/$GITHUB_BASE_REF` is the first lever, with a full run on a schedule.

## 6. Draft rule lines

Drafts for Codex to place. Each names the tool version, in the form the existing rules use.

### For `.claude/rules/go.md`

- rapid 1.3.0: Write property tests for pure core functions with `pgregory.net/rapid`. Do not use `testing/quick` or gopter.
- rapid 1.3.0: Run each property as a named subtest with `t.Run("name", rapid.MakeCheck(func(t *rapid.T) { ... }))`, and label every draw, `gen.Draw(t, "name")`.
- rapid 1.3.0: Build values with `rapid.Custom` and the combinators so they shrink. Use `Filter` only when no constructive generator exists.
- rapid 1.3.0: Keep properties free of I/O, time, and goroutines that outlive the check. They run in `check` under `-race -shuffle=on`.
- rapid 1.3.0: Reproduce a failure with the printed `-rapid.seed`, add the counterexample as a named table case, and delete the `testdata/rapid/` fail file rather than committing it.
- gremlins 0.6.0: Run `mise run check:mutation:go` before opening a pull request that touches a core package. It fails under 80% efficacy or 80% mutant coverage.
- gremlins 0.6.0: Kill a surviving mutant with a test. Do not lower a threshold or add a file to `exclude-files` without a recorded reason.
- gremlins 0.6.0: Keep shell packages out of the mutation scope. Only the pure core is scored.

### For `.claude/rules/python.md`

- hypothesis 6.168.1: Write property tests for pure core functions with `@given` under `tests/`. They run as ordinary tests in `check:pytest`.
- hypothesis 6.168.1: Import with `from hypothesis import given` and `from hypothesis import strategies as st` on separate lines, the form ruff's import sorting accepts.
- hypothesis 6.168.1: Register no `ci` profile. Hypothesis loads its built-in one when `CI` is set: derandomized, no deadline, no database.
- hypothesis 6.168.1: Do not commit `.hypothesis/` or add it to `.gitignore`. It ignores itself.
- hypothesis 6.168.1: Do not call `.example()` in tests or raise `max_examples` per test without a reason. Set `@settings(deadline=None)` only with a reason.
- mutmut 3.8.0: Run `mise run check:mutation:python` before opening a pull request that touches a core module. It fails under a score of 80%.
- mutmut 3.8.0: Configure with `source_paths` and `pytest_add_cli_args_test_selection`. `paths_to_mutate` and `tests_dir` are deprecated.
- mutmut 3.8.0: Delete `mutants/` before a run. Cached results do not notice a changed test.
- mutmut 3.8.0: Exempt an equivalent mutant with `# pragma: no mutate` and a reason on the same line. Kill every other survivor with a test.

## 7. Open items for the coordinator

- The notes path differs from the two paths the issues name, as recorded at the top.
- Seeds in CI: deterministic for the pull request gate, as proposed, or random.
- The mutation scope and the `paths` filters wait on the core layout from issue #58.
- Whether the mutation workflow is a required check, given the `paths` filter.
- Untested here and worth a line in the implementation work: installing gremlins through the mise `go:` backend, the Hypothesis wheel on the Linux runner, gremlins' off-by-default mutant types, `rapid.SyncTest`, and the tree-wide checks against a populated `mutants/`.
- The first real score per language, which issue #60 lists as evidence, cannot exist until core code does. The surviving-mutant evidence here is from the scratch modules.
