"""Compare a rescan summary with the published baseline and print a Markdown table.

Usage: python snapshot_diff.py BASELINE.json SNAPSHOT.json
Only numeric fields present in both files are compared.
"""
import json
import sys


def rows(base, snap, prefix=""):
    for k, v in base.items():
        if k not in snap:
            continue
        name = f"{prefix}{k}"
        if isinstance(v, dict) and isinstance(snap[k], dict):
            yield from rows(v, snap[k], name + ".")
        elif isinstance(v, (int, float)) and isinstance(snap[k], (int, float)) and not isinstance(v, bool):
            yield name, v, snap[k]


def main(base_path, snap_path):
    base, snap = json.load(open(base_path)), json.load(open(snap_path))
    out = ["| metric | published | rescan | change |", "|---|---|---|---|"]
    for name, a, b in rows(base, snap):
        out.append(f"| {name} | {a} | {b} | {round(b - a, 3):+} |")
    print("Rescan with the frozen rubric against the published baseline.\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
