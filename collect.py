"""Step 1: collect candidate public MCP server repos from GitHub search.

Writes data/repos.jsonl (one repo per line, deduped). Uses the gh CLI (already authed).
"""
import json, os, subprocess, pathlib, time

GH = os.environ.get("GH_BIN", "gh")
OUT = pathlib.Path(__file__).parent / "data" / "repos.jsonl"
QUERIES = [
    "topic:mcp-server",
    "topic:model-context-protocol",
    "mcp server in:name,description language:TypeScript",
    "mcp server in:name,description language:Python",
]
TARGET = 250  # collect a bit over 200 so filtering still leaves 200


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
    repos = [r for r in repos if "awesome" not in r["full_name"].lower() and r["size_kb"] < 150_000]
    repos = repos[:TARGET]
    OUT.write_text("".join(json.dumps(r) + "\n" for r in repos))
    print(f"{len(seen)} unique found, {len(repos)} kept -> {OUT}")


if __name__ == "__main__":
    main()
