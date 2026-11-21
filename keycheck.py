"""Re-clone repos flagged hardcoded_key and record each matching line, redacted, for hand review.

Every key-shaped string on a line is cut to its first 6 characters before anything is printed or
written, so full secrets are never stored. One row per matching line. Uses the same file filter
as scan.py, so it only reports hits in files that could have raised the flag.
"""
import json
import pathlib
import re
import subprocess

from scan import HYGIENE, TMP, CloneError, cloned, find_matches, iter_code_files, read_text

PAT = re.compile(HYGIENE["hardcoded_key"])
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "data" / "keyhits.jsonl"


def redact(line):
    return PAT.sub(lambda m: m.group(0)[:6] + "…REDACTED", line)


def key_hits(repo_dir):
    for p, rel in iter_code_files(repo_dir):
        text = read_text(p)
        if text is None:
            continue
        lines = text.split("\n")
        for ln in sorted({ln for _, ln, _ in find_matches(text, {"hardcoded_key": PAT})}):
            yield {"file": str(rel), "line": ln, "ctx": redact(lines[ln - 1]).strip()[:160]}


def main():
    with (ROOT / "data/scan.jsonl").open() as f:
        flagged = [s["full_name"] for s in map(json.loads, f) if s.get("hardcoded_key")]
    TMP.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for name in flagged:
            try:
                with cloned(name) as d:
                    for hit in key_hits(d):
                        f.write(json.dumps({"repo": name, **hit}) + "\n")
            except (CloneError, subprocess.TimeoutExpired, OSError) as e:
                print("skip", name, type(e).__name__, flush=True)
                continue
            print("done", name, flush=True)


if __name__ == "__main__":
    main()
