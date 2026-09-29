#!/usr/bin/env bash
# Compare digests in memory; print only whether the receiver saw the guest placeholder.
set -eu
receiver_log=${1:?receiver log required}
request_path=${2:?request path required}
receiver_hash=$(
    mise exec -- python - "$receiver_log" "$request_path" <<'PY'
import json
import sys

records = [json.loads(line) for line in open(sys.argv[1])]
matches = [r for r in records if r.get("path") == sys.argv[2]]
assert len(matches) == 1
print(matches[0]["auth_sha256_16"])
PY
)
# The guest shell expands BV05_TOKEN inside the sandbox.
# shellcheck disable=SC2016
mise exec -- sbx exec bv05-kit sh -c '
guest_hash=$(printf "Bearer %s" "$BV05_TOKEN" | sha256sum | cut -c1-16)
if [ "$guest_hash" = "$1" ]; then
    printf "receiver bearer matches guest placeholder\n"
else
    printf "receiver bearer differs from guest placeholder\n"
fi
' sh "$receiver_hash"
