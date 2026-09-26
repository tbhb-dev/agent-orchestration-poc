#!/usr/bin/env python3
"""Summarize the retained controlled captures and check text reconstruction."""
import collections
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "evidence"
summary = {}
for name in ["resume-attached", "read-metadata-live", "proxy-reconnect", "late-attach"]:
    rows = [json.loads(line) for line in (root / (name + ".jsonl")).read_text().splitlines()]
    counts = collections.Counter()
    text = collections.defaultdict(str)
    first = {}
    messages = []
    commands = []
    for row in rows:
        msg = row["data"]
        method = msg.get("method")
        if not method:
            continue
        counts[method] += 1
        p = msg.get("params", {})
        if method == "item/agentMessage/delta":
            key = p["itemId"]
            text[key] += p["delta"]
            first.setdefault(key, row["observed_at"])
        if method == "item/completed":
            item = p["item"]
            if item["type"] == "agentMessage":
                key = item["id"]
                messages.append({"id":key, "text":item["text"], "phase":item.get("phase"),
                    "deltas_match":text[key] == item["text"], "first_delta_at":first.get(key),
                    "completed_at":row["observed_at"]})
            elif item["type"] == "commandExecution":
                commands.append({"id":item["id"], "output":item["aggregatedOutput"],
                    "exitCode":item["exitCode"], "completed_at":row["observed_at"]})
    summary[name] = {"notification_counts":dict(counts), "messages":messages, "commands":commands}

# The full beta response was observed from start to finish.
beta = next(m for m in summary["resume-attached"]["messages"] if m["text"].startswith("STREAM_FINAL_BETA"))
assert beta["deltas_match"], "Assistant text deltas did not reconstruct the completed item"
assert not summary["read-metadata-live"]["messages"], "Metadata reader unexpectedly received assistant items"
assert "STREAM_BETA_ONE" not in summary["resume-attached"]["commands"][0]["output"]
assert all("STREAM_GAMMA_"+word in summary["late-attach"]["commands"][0]["output"] for word in ["ONE", "TWO", "THREE"])

timing = [json.loads(l) for l in (root/"rollout-beta-timing.jsonl").read_text().splitlines()]
persisted = next(r for r in timing if r["role"] == "assistant" and "STREAM_FINAL_BETA" in r["markers"])
summary["beta_timing"] = {
    "first_final_delta_at": beta["first_delta_at"],
    "completed_item_at": beta["completed_at"],
    "rollout_message_observed_at": persisted["observed_at"],
    "first_delta_to_rollout_seconds": persisted["observed_at"]-beta["first_delta_at"],
    "first_delta_to_completed_seconds": beta["completed_at"]-beta["first_delta_at"],
}
control = [json.loads(l) for l in (root/"control-live.jsonl").read_text().splitlines()]
summary["terminal"] = {"control_records":len(control),
    "output_records":sum(r["line"].startswith("%output ") for r in control),
    "raw_bytes":(root/"terminal.raw").stat().st_size,
    "escape_bytes":(root/"terminal.raw").read_bytes().count(b"\x1b")}
(root/"analysis.json").write_text(json.dumps(summary, indent=2)+"\n")
print(json.dumps({"beta_timing":summary["beta_timing"], "terminal":summary["terminal"], "checks":"passed"},indent=2))
