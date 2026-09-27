#!/usr/bin/env sh
# Resolve and check the reviewer identity before each gh command.
set -eu
exec mise exec -- uv run python -m agent_orchestration_poc.shell.review_identity "$@"
