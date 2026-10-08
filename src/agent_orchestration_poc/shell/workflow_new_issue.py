"""Validate a local issue before asking GitHub to create it."""

import argparse
import logging
import subprocess
import sys

from agent_orchestration_poc.core.workflow_forms import validate_issue
from agent_orchestration_poc.shell.workflow_forms import _reference

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Create only issues that pass the shared workflow validator."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--label", action="append", required=True)
    parser.add_argument("--body-file", type=argparse.FileType("r"), required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    body = args.body_file.read()
    args.body_file.close()
    findings = validate_issue(args.title, body, tuple(args.label), _reference())
    if findings:
        for finding in findings:
            LOGGER.error("%s", finding)
        return 1
    command = ["gh", "issue", "create", "--title", args.title, "--body-file", "-"]
    for label in args.label:
        command.extend(("--label", label))
    return subprocess.run(command, input=body, text=True, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
