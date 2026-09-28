# Work model backfill runner evidence

## Core gap disposition

[Verified] The four pure contract corrections in `work_model_backfill.py` derive parent goal and finish line bodies, incident records, and draft classification bodies from approved table rows. CP1 rejects a mismatched draft key and title and checks an existing draft's class and Size. Snapshot completeness requires a separate complete receipt for each issue's native field values, blockers, and sub-issues, including all pages.

[Documented] [The approved version 3 model](work-model-tables/2026-09-27-work-model-v3-final.md) says drafts have Validation and Validation detail as Project fields and that the Actions validator supplies their validity. The assignment and parent tables provide no validation result or detail to derive. CP13 therefore excludes those two validator-owned values from target equality. The runner must retain their observed values in CP13 for the operator's separate validator review. This applies the coordinator's disposition in [PR #223](https://github.com/tbhb-dev/agent-orchestration-poc/pull/223#issuecomment-5861216316).

[Untested] No live CP1 or CP13 has been collected and no backfill write has been made. The runner implementation will add request ledgers, response statuses, headers, and command exit codes in this report.
