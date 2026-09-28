---
title: Experiments
description: Experiment layout and the existing system assessment.
---

Create experiment directories in dispatch order as `experiments/NN-slug/`. Each new directory needs a Codex-written `README.md`, scripts as needed, an `evidence/` directory for raw output, and `versions.md` recording the versions tested. `mise run check:experiments` checks the directory name and required entries.

The existing [00-system-assessment](https://github.com/tbhb-dev/agent-orchestration-poc/tree/main/experiments/00-system-assessment) records the September 26 host inventory, dependency clones, permission facts, model calls, and harness, NATS, and GitHub Projects research. It predates the directory rule and is explicitly exempt in `scripts/check-experiments.sh`. Its raw output is in `evidence.md`, with versions in `versions.md`.

Phase 2 tests bootstrap behavior. Phase 3 tests the container, authentication, terminal, and bus questions in the [plan](/project/plan/#phase-3-research-and-experiments). Record evidence labels and limits with each result before proposing a design decision.
