# BV-01 r8 capture trim

- Full capture SHA-256: `4271c118de3e428e87e6c080c996268e746749312663e68bdfdd071fe1939090`; 10,430 JSONL lines and 22,887,994 bytes. The full capture remains outside Git at `/private/tmp/bv01-228-codex-headless/file-opens-relay-r8.json`.
- Trimmed gzip SHA-256: `dddc3453ce2ecc601aae21f708ae39d2bc1d3a3ed7ca95ad5a19fd2000494f57`; 295 JSONL lines and 22,497 bytes on disk.
- Filter: retain open events from root PIDs recorded in `root.pid`. Include descendants when `listener.jsonl` ancestry or `process-tree.txt` reaches that root. Where the listener recorded start times, require the time when the captured process started to match within two seconds. Also retain events whose opened path contains `audit-positive-relay-r8`.
- Selection counts: 293 recorded process-instance events and two positive-control events. The eligible cell PIDs are launch root 13462, its `caffeinate` child 13877, Bash child 13885, and probe client 13892. The retained cell events comprise 276 from the root, three from Bash, and 14 from the probe. `caffeinate` has zero retained opens. The positive-control events came from outside the cell tree.
- Secret review: these `eslogger` records contain file-open paths and metadata, without file contents. One retained root event refers to `/Library/Keychains/System.keychain`. A path search found zero matches for 1Password or the operator's real Codex or Claude configuration homes. The committed cell and preflight files use the literal fixture value `not-a-real-key`.
- Limits: every retained cell event matched a recorded process start time within two seconds. The selected events cannot establish whether other files were opened or read, and an open event alone cannot establish a read.
- Listener records excluded: [].
