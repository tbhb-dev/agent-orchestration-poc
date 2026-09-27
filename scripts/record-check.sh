#!/usr/bin/env sh
set -eu
case $0 in
    */*) script_dir=${0%/*} ;;
    *) script_dir=. ;;
esac
script_dir=$(CDPATH='' cd -- "$script_dir" && pwd)
if [ "${PYTHONPATH+x}" = x ]; then
    CHECK_TIMING_PARENT_PYTHONPATH=$PYTHONPATH
    CHECK_TIMING_PYTHONPATH_WAS_SET=1
else
    CHECK_TIMING_PARENT_PYTHONPATH=''
    CHECK_TIMING_PYTHONPATH_WAS_SET=0
fi
export CHECK_TIMING_PARENT_PYTHONPATH CHECK_TIMING_PYTHONPATH_WAS_SET
PYTHONPATH="$script_dir/../src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python -S -m agent_orchestration_poc.shell.check_timings "$@"
