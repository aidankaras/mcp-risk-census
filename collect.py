"""Step 1: collect candidate public MCP server repos from GitHub search.

Writes data/repos.jsonl (one repo per line, deduped) and data/collect_meta.json (counts and
queries for the run). Uses the gh CLI (already authed).

`python collect.py --refresh-stars PATH` updates only the star counts in an existing repos.jsonl
(used by the monthly rescan, so the candidate list and descriptions stay fixed).
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time

GH = os.environ.get("GH_BIN", "gh")
OUT = pathlib.Path(__file__).parent / "data" / "repos.jsonl"
META = OUT.with_name("collect_meta.json")
QUERIES = [
    "topic:mcp-server",
    "topic:model-context-protocol",
    "mcp server in:name,description language:TypeScript",
    "mcp server in:name,description language:Python",
]
TARGET = 250  # candidates passed to scan.py; analyze.py then keeps the MCP servers among them
MAX_SIZE_KB = 150_000


def search(q, page):
    r = subprocess.run([GH, "api", "-X", "GET", "search/repositories",
                        "-f", f"q={q} fork:false archived:false", "-f", "sort=stars",
                        "-f", "per_page=100", "-f", f"page={page}"],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)["items"]


def main():
    OUT.parent.mkdir(exist_ok=True)
    seen = {}
    for q in QUERIES:
        for page in (1, 2):
            try:
                items = search(q, page)
            except subprocess.CalledProcessError as e:  # usually search rate limit
                print(f"skip {q!r} p{page}: {e.stderr.strip()[:120]}")
                time.sleep(20)
                continue
            for it in items:
                seen.setdefault(it["full_name"], {
                    "full_name": it["full_name"], "stars": it["stargazers_count"],
                    "language": it["language"], "description": (it["description"] or "")[:200],
                    "pushed_at": it["pushed_at"], "license": (it["license"] or {}).get("spdx_id"),
                    "size_kb": it["size"], "default_branch": it["default_branch"],
                    "found_by": q,
                })
            time.sleep(2)  # search API: 30 req/min
    repos = sorted(seen.values(), key=lambda r: -r["stars"])
    # skip awesome-lists / giant monorepos (not a single server)
    repos = [r for r in repos if "awesome" not in r["full_name"].lower() and r["size_kb"] < MAX_SIZE_KB]
    after_filter = len(repos)
    repos = repos[:TARGET]
    OUT.write_text("".join(json.dumps(r) + "\n" for r in repos))
    META.write_text(json.dumps({
        "collected_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "queries": QUERIES, "unique_found": len(seen), "after_awesome_and_size_filter": after_filter,
        "kept": len(repos), "target": TARGET, "max_size_kb": MAX_SIZE_KB}, indent=2))
    print(f"{len(seen)} unique found, {len(repos)} kept -> {OUT}")


def refresh_stars(path):
    """Replace star counts in an existing repos.jsonl with current ones; keep everything else."""
    path = pathlib.Path(path)
    with path.open() as f:
        repos = [json.loads(line) for line in f]
    for r in repos:
        res = subprocess.run([GH, "api", f"repos/{r['full_name']}", "--jq", ".stargazers_count"],
                             capture_output=True, text=True, check=False)
        r["stars_refreshed"] = res.returncode == 0
        if res.returncode == 0:
            r["stars"] = int(res.stdout.strip())
    path.write_text("".join(json.dumps(r) + "\n" for r in repos))
    print(f"refreshed {sum(r['stars_refreshed'] for r in repos)}/{len(repos)} star counts in {path}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--refresh-stars":
        refresh_stars(sys.argv[2])
    else:
        main()
