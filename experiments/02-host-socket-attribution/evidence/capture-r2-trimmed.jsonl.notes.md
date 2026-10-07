# BV-01 r2 capture trim

- Full capture SHA-256: `9377ba7edc76d89c15202cea885f38827a21748770478cd0b4f5dd24972c6d47`. It contains 1425046 JSONL lines.
- Trimmed gzip SHA-256: `f25d83805480820c8f8fe28604bb2452887a821759736bca4f7450f5014b89ce`. It contains 661 JSONL lines and occupies 0.000 GiB on disk.
- Filter: retain open events from root PIDs recorded in `root.pid`. Include descendants when `listener.jsonl` ancestry or `process-tree.txt` reaches that root. Where the listener recorded start times, require the event's process start time to match within two seconds. Also retain events whose opened path contains `audit-positive-relay-r2`.
- Selection counts: 8 positive controls. Records tied to a process instance: 136. Root or snapshot PID matches without start times: 517. The included PIDs are 14300, 14426, 19738, and 86910.
- Limits: root-only records lack incarnation timestamps, so their PID matches are weaker. This subset of observed events does not establish that other file opens did not occur.
- Listener records excluded: none.
