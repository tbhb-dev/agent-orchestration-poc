#!/usr/bin/env sh
# Capture only lifecycle fields from this disposable Claude session.
set -eu
probe_dir=${EXP214_CAPTURE_DIR:?}
mise exec -- jq -c '{hook_event_name,session_id,stop_hook_active}' >> "$probe_dir/claude-hook.jsonl"
