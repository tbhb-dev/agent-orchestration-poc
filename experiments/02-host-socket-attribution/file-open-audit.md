# File-open audit for stage two

## Proposed capture

**Documented:** `/usr/bin/opensnoop` on macOS 26.5.1 build 25F80 is a DTrace wrapper. Its installed manual says it records open paths, PID, PPID, descriptor, and optional open flags, and requires root. The installed script invokes `/usr/sbin/dtrace` and supports `-F` for flags and `-e` for error numbers. `/usr/bin/fs_usage` also requires root and reports filesystem calls, but its manual says path output can be truncated. Runtime behavior for a harness remains untested.

The operator would start a system-wide capture before any of the four launches and keep it running through exit. Stop only that capture after all descendants exit. A root-only raw trace remains under one disposable profile until it has been inspected and redacted. The command is:

```sh
sudo /usr/bin/opensnoop -F -e -s > /private/tmp/bv01-228-codex-headless/file-opens.raw 2> /private/tmp/bv01-228-codex-headless/file-opens.err &
audit_pid=$!
```

Record `audit_pid`, the start time, the four launch-root PIDs and start times, every observed descendant PID and start time, the capture exit status, and any DTrace errors. Before the harness launch, open a harmless file inside the disposable profile as a positive control and require the trace to show it. Filter raw trace by the recorded process instances after capture. Inspect paths under the operator's actual Codex and Claude homes, the home-relative `.claude.json`, 1Password, and keychain database locations without opening those locations. Do not commit raw paths or arguments until an operator reviews and redacts them.

## Trace interpretation

**Inference:** a successful open event for a recorded process and sensitive path proves that process opened the path under the trace's conditions. Open flags can distinguish an open with read access from one with write access, but flags alone do not prove bytes were read or written. A read can use an inherited descriptor or a memory mapping without a new open after capture begins. A write can use a descriptor opened before capture. Failed opens show attempted access, not access to file contents.

**Untested:** no file-open trace has run on this host for these harnesses. Absence of an event does not prove absence of a read. The installed DTrace script can fail to obtain a pathname. Protected processes or SIP can limit DTrace visibility. The proposed command is system-wide because PID filters can miss new helper processes. Separate process records support descendant attribution. The capture itself may expose private paths, so the operator must handle it. A write-only before/after snapshot cannot prove absence of reads.

This method cannot establish that no read happened on macOS 25. If the operator requires that claim before stage two, the smallest stronger system change is an operator-managed, entitled Endpoint Security file-open monitor, started before launch and scoped by the four process trees. The operator would approve the privileged monitor and verify a positive-control read. Its coverage of open, inherited descriptors, and memory maps needs separate review. Until then, report `configuration and keychain reads unverified` for each harness cell. Do not change SIP or install a monitor as part of this stage-one work.
