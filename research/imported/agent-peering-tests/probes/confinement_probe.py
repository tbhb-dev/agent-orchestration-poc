#!/usr/bin/env python3
"""Report whether a process is confined by a Seatbelt sandbox (macOS).

Run OUTSIDE any sandbox, from the operator's terminal:

    python3 probes/confinement_probe.py <pid> [<pid> ...]
    python3 probes/confinement_probe.py self

Calls the private libsystem_sandbox function sandbox_check(pid, NULL, 0).
The return-value meaning is not documented by Apple, so calibrate first:
run it against your own shell ("self" checks this process, which should be
unconfined) and against a process started from a sandboxed tool call, which
should be confined. Only trust the results once both calibration cases come
out as expected.
"""
import ctypes
import os
import subprocess
import sys

LIB = "/usr/lib/system/libsystem_sandbox.dylib"


def describe(pid):
    out = subprocess.run(
        ["ps", "-ww", "-o", "ppid=", "-o", "args=", "-p", str(pid)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out or "<no such process>"


def main():
    if sys.platform != "darwin":
        print("macOS only", file=sys.stderr)
        return 2
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    lib = ctypes.CDLL(LIB, use_errno=True)
    fn = lib.sandbox_check
    fn.restype = ctypes.c_int
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]

    for arg in sys.argv[1:]:
        pid = os.getpid() if arg == "self" else int(arg)
        ctypes.set_errno(0)
        rc = fn(pid, None, 0)
        err = ctypes.get_errno()
        if rc == 1:
            verdict = "CONFINED"
        elif rc == 0:
            verdict = "UNCONFINED"
        else:
            verdict = f"UNKNOWN (rc={rc}, errno={err} {os.strerror(err) if err else ''})"
        print(f"pid={pid} {verdict}")
        print(f"    {describe(pid)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
