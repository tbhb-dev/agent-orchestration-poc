#!/usr/bin/env python3
"""Check whether this process can read another process's arguments (macOS).

Run from INSIDE a harness tool call:

    python3 probes/procargs_probe.py <pid>

Uses sysctl(KERN_PROCARGS2), the call `ps -E` relies on. Prints the target's
executable path and arguments, and only the NAMES of its environment
variables, never their values, so nothing sensitive lands in a transcript.
Reports the exact error if the read is denied.
"""
import ctypes
import ctypes.util
import os
import struct
import sys

CTL_KERN = 1
KERN_ARGMAX = 8
KERN_PROCARGS2 = 49


def sysctl(mib, size):
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    arr = (ctypes.c_int * len(mib))(*mib)
    buf = ctypes.create_string_buffer(size)
    sz = ctypes.c_size_t(size)
    rc = libc.sysctl(arr, len(mib), buf, ctypes.byref(sz), None, ctypes.c_size_t(0))
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return buf.raw[: sz.value]


def main():
    if sys.platform != "darwin":
        print("macOS only", file=sys.stderr)
        return 2
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    pid = int(sys.argv[1])

    try:
        argmax = struct.unpack("i", sysctl([CTL_KERN, KERN_ARGMAX], 4))[0]
        raw = sysctl([CTL_KERN, KERN_PROCARGS2, pid], argmax)
    except OSError as exc:
        print(f"pid={pid} DENIED: {exc}")
        return 1

    argc = struct.unpack("i", raw[:4])[0]
    fields = raw[4:].split(b"\0")
    exec_path = fields[0].decode(errors="replace")
    rest = fields[1:]
    while rest and rest[0] == b"":
        rest = rest[1:]
    args = [f.decode(errors="replace") for f in rest[:argc]]
    env_names = [
        f.split(b"=", 1)[0].decode(errors="replace")
        for f in rest[argc:]
        if b"=" in f
    ]

    print(f"pid={pid} READABLE")
    print(f"  exec_path: {exec_path}")
    print(f"  args: {args}")
    print(f"  env var names ({len(env_names)}): {', '.join(sorted(env_names))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
