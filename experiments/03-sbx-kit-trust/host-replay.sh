#!/usr/bin/env bash
# Host-only replay. This never invokes sbx or changes a trust store.
set -euo pipefail

cd "$(dirname "$0")/../.."
scratch=$(mktemp -d /private/tmp/bv05-host-replay.XXXXXX)
receiver_pid=
cleanup() {
    if [ -n "$receiver_pid" ]; then
        kill "$receiver_pid" 2>/dev/null || true
        wait "$receiver_pid" 2>/dev/null || true
    fi
    rm -rf "$scratch"
    printf '%s\n' 'cleanup: stopped receiver and removed scratch directory'
}
trap cleanup EXIT

fixture=experiments/03-sbx-kit-trust/fixture.py
port=18453
printf 'scratch=%s\n' "$scratch"
printf '%s\n' '$ fixture.py pki --root <scratch>/pki'
PYTHONSAFEPATH=1 mise exec -- python "$fixture" pki --root "$scratch/pki"
printf '%s\n' '$ fixture.py kit --root <scratch>/pki --kit <scratch>/kit --port 18453'
PYTHONSAFEPATH=1 mise exec -- python "$fixture" kit --root "$scratch/pki" --kit "$scratch/kit" --port "$port"

for leaf in valid wrong-host expired unrelated; do
    printf '$ openssl verify -CAfile <scratch>/pki/ca.crt -verify_hostname localhost <scratch>/pki/%s.crt\n' "$leaf"
    if mise exec -- openssl verify -CAfile "$scratch/pki/ca.crt" -verify_hostname localhost "$scratch/pki/$leaf.crt"; then
        printf 'exit=0\n'
    else
        printf 'exit=%s\n' "$?"
    fi
done

start_receiver() {
    printf '%s' '$ fixture.py serve --root <scratch>/pki --leaf valid --port 18453 --log <scratch>/receiver.jsonl --deliveries <scratch>/deliveries.jsonl'
    if [ "$#" -gt 0 ]; then
        printf ' %s' "$@"
    fi
    printf '\n'
    PYTHONSAFEPATH=1 mise exec -- python "$fixture" serve --root "$scratch/pki" --leaf valid --port "$port" --log "$scratch/receiver.jsonl" --deliveries "$scratch/deliveries.jsonl" "$@" >"$scratch/server.stdout" 2>"$scratch/server.stderr" &
    receiver_pid=$!
    sleep 1
    kill -0 "$receiver_pid"
    cat "$scratch/server.stdout" "$scratch/server.stderr"
}

start_receiver
printf '%s\n' '$ curl --cacert <scratch>/pki/ca.crt https://localhost:18453/host-control'
mise exec -- curl -sS --cacert "$scratch/pki/ca.crt" "https://localhost:$port/host-control"
printf '%s\n' '$ curl --max-time 5 https://localhost:18453/host-untrusted'
if mise exec -- curl -sS --max-time 5 "https://localhost:$port/host-untrusted"; then
    printf 'exit=0\n'
else
    printf 'exit=%s\n' "$?"
fi
printf '%s\n' '$ kill receiver; wait receiver'
kill "$receiver_pid"
wait "$receiver_pid" 2>/dev/null || true
receiver_pid=

start_receiver --client-ca
printf '%s\n' '$ curl --cacert <scratch>/pki/ca.crt https://localhost:18453/no-client-cert'
mise exec -- curl -sS --cacert "$scratch/pki/ca.crt" "https://localhost:$port/no-client-cert"
printf '%s\n' '$ curl --cacert <scratch>/pki/ca.crt --cert <scratch>/pki/client.crt --key <scratch>/pki/client.key https://localhost:18453/with-client-cert'
mise exec -- curl -sS --cacert "$scratch/pki/ca.crt" --cert "$scratch/pki/client.crt" --key "$scratch/pki/client.key" "https://localhost:$port/with-client-cert"
printf '%s\n' '$ kill receiver; wait receiver'
kill "$receiver_pid"
wait "$receiver_pid" 2>/dev/null || true
receiver_pid=
printf '%s\n' '$ cat <scratch>/receiver.jsonl'
cat "$scratch/receiver.jsonl"
