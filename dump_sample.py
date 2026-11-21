"""Sample 20 servers (stratified by stars) and dump capability-signal matches with context
for hand-labeling. Output: data/label_dump.jsonl

Matching uses scan.find_matches on the whole file, the same way scan.py counts signals, so a
match that spans lines (sql_raw) shows up here too. Context is capped at MAX_SHOWN hits per
signal; n_hits records the full count so readers can see where the cap applied.
"""
import json
import pathlib
import random
import subprocess

from scan import ALL_PATTERNS, SIGNALS, TMP, CloneError, cloned, find_matches, iter_code_files, read_text

ROOT = pathlib.Path(__file__).parent
MAX_SHOWN = 25
SEED = 7


def sample_servers(rows, k=20):
    rows = sorted(rows, key=lambda r: -r["stars"])
    n = len(rows)
    a, b = round(n / 3), round(2 * n / 3)
    random.seed(SEED)
    # stratified: 7 from the top third by stars, 7 middle, 6 bottom
    return [r for t in (rows[:a], rows[a:b], rows[b:]) for r in random.sample(t, min(len(t), 7))][:k]


def capability_hits(repo_dir):
    pats = {k: ALL_PATTERNS[k] for k in SIGNALS}
    hits = []
    for p, rel in iter_code_files(repo_dir):
        text = read_text(p)
        if text is None:
            continue
        lines = text.split("\n")
        for sig, ln, _ in find_matches(text, pats):
            hits.append({"sig": sig, "file": str(rel)[:90], "line": ln, "ctx": lines[ln - 1].strip()[:160]})
    return hits


def main():
    with (ROOT / "data/servers.jsonl").open() as f:
        rows = [json.loads(line) for line in f]
    TMP.mkdir(parents=True, exist_ok=True)
    with (ROOT / "data/label_dump.jsonl").open("w") as out:
        for r in sample_servers(rows):
            try:
                with cloned(r["full_name"]) as d:
                    hits = capability_hits(d)
            except (CloneError, subprocess.TimeoutExpired, OSError) as e:
                print("skip", r["full_name"], type(e).__name__, flush=True)
                continue
            by_sig = {k: [h for h in hits if h["sig"] == k] for k in SIGNALS}
            out.write(json.dumps({"repo": r["full_name"], "stars": r["stars"], "loc": r["loc"],
                                  "n_hits": {k: len(v) for k, v in by_sig.items()},
                                  "hits": {k: v[:MAX_SHOWN] for k, v in by_sig.items()}}) + "\n")
            print("dumped", r["full_name"], len(hits), flush=True)


if __name__ == "__main__":
    main()
