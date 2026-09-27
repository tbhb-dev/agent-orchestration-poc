"""Run gh commands with an explicitly checked reviewer credential."""

import os
import subprocess
import sys
from collections.abc import Sequence

from agent_orchestration_poc.core.review_identity import (
    REVIEWER,
    reviewer_command_allowed,
    reviewer_identity_matches,
    reviewer_token_present,
)


def main(arguments: Sequence[str] | None = None) -> int:
    """Resolve the reviewer token, check identity, then run one command."""
    argv = list(sys.argv[1:] if arguments is None else arguments)
    if not reviewer_command_allowed(argv):
        sys.stderr.write("reviewer-gh: command is not allowed\n")
        return 91

    lookup_env = os.environ.copy()
    lookup_env.pop("GH_TOKEN", None)
    lookup_env.pop("GITHUB_TOKEN", None)
    try:
        lookup = subprocess.run(
            ["gh", "auth", "token", "--user", REVIEWER],
            capture_output=True,
            text=True,
            check=False,
            env=lookup_env,
        )
        token = lookup.stdout.strip()
        if lookup.returncode != 0 or not reviewer_token_present(token):
            sys.stderr.write("reviewer-gh: reviewer token lookup failed\n")
            return 90

        review_env = {**lookup_env, "GH_TOKEN": token}
        identity = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=False,
            env=review_env,
        )
        if identity.returncode != 0 or not reviewer_identity_matches(
            identity.stdout.strip()
        ):
            sys.stderr.write("reviewer-gh: effective account is not tbhbbot\n")
            return 91
        return subprocess.run(["gh", *argv], env=review_env, check=False).returncode
    except OSError:
        sys.stderr.write("reviewer-gh: gh command failed\n")
        return 92


if __name__ == "__main__":
    sys.exit(main())
