"""Scanner validation: compare scan flags with the hand labels for the 20 sampled repos.

Inputs: data/hand_labels.json (labels), data/scan.jsonl (flags), data/label_dump.jsonl (what the
reviewer was shown), data/servers.jsonl (census rates). Output: data/validation.json.

Precision and recall get 95% Wilson intervals. The labels came from an LLM reviewer (see README),
and n is small, so the intervals are wide.
"""
import json
import math
import pathlib
import random

from analyze import read_jsonl
from scan import SIGNALS

ROOT = pathlib.Path(__file__).parent
ADJUST = ("shell_exec", "fs_write", "outbound_http")  # signals with enough flagged repos to adjust
N_BOOT = 10_000
SEED = 0


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 2), round(min(1.0, centre + half), 2)]


def confusion(items, sig):
    flagged = sum(1 for it in items if it["flag"][sig])
    capable = sum(1 for it in items if it["label"][sig])
    tp = sum(1 for it in items if it["flag"][sig] and it["label"][sig])
    return flagged, capable, tp


def adjusted_rate(raw, items, sig, rng):
    """raw x precision / recall, with a bootstrap 95% interval over the labeled repos."""
    flagged, capable, tp = confusion(items, sig)
    point = raw * (tp / flagged) / (tp / capable)
    draws = []
    for _ in range(N_BOOT):
        f, c, t = confusion([rng.choice(items) for _ in items], sig)
        if f and c and t:
            draws.append(raw * (t / f) / (t / c))
    draws.sort()
    lo, hi = draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]
    return {"raw_pct": round(100 * raw), "adjusted_pct": round(100 * point),
            "adjusted_ci95_pct": [round(100 * lo), min(100, round(100 * hi))]}


def main():
    labels = json.loads((ROOT / "data/hand_labels.json").read_text())
    scan = {s["full_name"]: s for s in read_jsonl(ROOT / "data/scan.jsonl") if "error" not in s}
    dump = {d["repo"]: d for d in read_jsonl(ROOT / "data/label_dump.jsonl")}
    servers = read_jsonl(ROOT / "data/servers.jsonl")
    items = [{"repo": lab["repo"],
              "flag": {k: bool(scan[lab["repo"]][k]) for k in SIGNALS},
              "label": {k: lab[k] for k in SIGNALS},
              "shown": {k: bool(dump[lab["repo"]]["hits"][k]) for k in SIGNALS}} for lab in labels]

    out = {}
    for sig in SIGNALS:
        flagged, capable, tp = confusion(items, sig)
        not_shown = sum(1 for it in items if it["flag"][sig] and not it["shown"][sig])
        out[sig] = {"flagged": flagged, "truly_capable": capable, "true_pos": tp,
                    "precision": round(tp / flagged, 2) if flagged else None,
                    "precision_ci95": wilson(tp, flagged),
                    "recall": round(tp / capable, 2) if capable else None,
                    "recall_ci95": wilson(tp, capable),
                    "flagged_but_no_hit_shown": not_shown}
    rng = random.Random(SEED)
    out["adjusted_rates"] = {
        "method": "census rate x precision / recall; 95% interval from a bootstrap over the 20 labeled repos",
        **{sig: adjusted_rate(sum(1 for r in servers if r[sig]) / len(servers), items, sig, rng)
           for sig in ADJUST}}
    (ROOT / "data/validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
