"""Step 2: static first-pass scan of each repo (shallow clone, regex signals, delete clone).

Signals are heuristics, not verdicts; see RUBRIC.md and the validation section of the README.
Appends to data/scan.jsonl; resumable (skips repos already scanned without error, retries failures).
Clones are depth-1, one at a time, and deleted after scanning. Nothing in a scanned repo is executed.

keycheck.py and dump_sample.py reuse iter_code_files() and find_matches() so that all three
scripts look at the same files and match the same way.
"""
import bisect
import contextlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).parent
REPOS = ROOT / "data" / "repos.jsonl"
OUT = ROOT / "data" / "scan.jsonl"
TMP = pathlib.Path(os.environ.get("MCP_CENSUS_TMP", tempfile.gettempdir())) / "mcp-census-clones"
CLONE_TIMEOUT = 180
# Rubric v2 (this file). The published baseline in data/scan.jsonl was produced by rubric v1,
# scan.py at commit 515fada; see RUBRIC.md for the differences.
RUBRIC_VERSION = 2
CODE_EXT = {".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs",
            ".go", ".rs", ".java", ".kt", ".swift", ".cs", ".rb"}
# GitHub shows a security policy from any of these locations.
SECURITY_MD_DIRS = ("", ".github", "docs")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "vendor", "test", "tests", "__tests__", "examples", "docs"}

# capability signals: what the server can do on the host / network
SIGNALS = {
    "shell_exec": r"\b(child_process|execSync|spawn\(|subprocess\.|os\.system|exec\.Command|Runtime\.getRuntime)",
    "fs_write": r"\b(writeFile|fs\.write|open\([^)]*['\"]w|os\.remove|unlink|rmSync|shutil\.rmtree|os\.WriteFile)",
    "outbound_http": r"\b(fetch\(|axios|requests\.(get|post)|httpx|urllib|http\.Get|reqwest)",
    "eval_dynamic": r"\b(eval\(|new Function\(|exec\(compile|vm\.runIn)",
    "sql_raw": r"(execute\(\s*f['\"]|\.query\(\s*`[^`]*\$\{)",
}
# hygiene signals
HYGIENE = {
    "hardcoded_key": r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[0-9A-Za-z-]{20,})",
    "auth_mentioned": r"\b(oauth|OAuth|bearer|Authorization|api[_-]?key)\b",
    "path_guard": r"(allowed_?dir|allowedDirectories|realpath|path\.resolve\(.*startsWith|is_relative_to)",
    "input_schema": r"(zod|z\.object|inputSchema|pydantic|BaseModel)",
}
TRANSPORT = {"http_sse": r"(\bSSE\b|\bsse\b|SSEServerTransport|StreamableHTTP|streamable-http)"}
ALL_PATTERNS = {k: re.compile(p) for d in (SIGNALS, HYGIENE, TRANSPORT) for k, p in d.items()}


class CloneError(Exception):
    pass


@contextlib.contextmanager
def cloned(full_name):
    """Shallow-clone a public GitHub repo into TMP; always delete it afterwards (also on timeout)."""
    dest = TMP / full_name.replace("/", "__")
    shutil.rmtree(dest, ignore_errors=True)
    try:
        cl = subprocess.run(["git", "clone", "-q", "--depth", "1",
                             f"https://github.com/{full_name}.git", str(dest)],
                            capture_output=True, text=True, timeout=CLONE_TIMEOUT, check=False)
        if cl.returncode != 0:
            raise CloneError(cl.stderr[-300:].strip())
        yield dest
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def iter_code_files(repo_dir):
    """Yield (path, relative path) for every source file the scanner reads."""
    for p in sorted(repo_dir.rglob("*")):
        rel = p.relative_to(repo_dir)
        if p.is_file() and p.suffix in CODE_EXT and not set(rel.parts) & SKIP_DIRS:
            yield p, rel


def read_text(path):
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return None


def find_matches(text, patterns):
    """Yield (name, line_no, matched_text) for every match of every pattern in the whole text.

    Patterns run on the full file, not line by line, because some can span lines (sql_raw's
    template literal). line_no is the 1-based line where the match starts.
    """
    newlines = [m.start() for m in re.finditer("\n", text)]
    for name, pat in patterns.items():
        for m in pat.finditer(text):
            yield name, bisect.bisect_left(newlines, m.start()) + 1, m.group(0)


def scan_dir(repo_dir):
    """Signal counts for a checked-out repo."""
    counts = {k: 0 for k in ALL_PATTERNS}
    n_files = loc = 0
    for p, _ in iter_code_files(repo_dir):
        txt = read_text(p)
        if txt is None:
            continue
        n_files += 1
        loc += txt.count("\n")
        for name, _, _ in find_matches(txt, ALL_PATTERNS):
            counts[name] += 1
    has_security_md = any(p.name.upper() == "SECURITY.MD"
                          for d in SECURITY_MD_DIRS if (repo_dir / d).is_dir()
                          for p in (repo_dir / d).iterdir() if p.is_file())
    return {"code_files": n_files, "loc": loc, "security_md": has_security_md, **counts}


def scan_repo(r):
    with cloned(r["full_name"]) as dest:
        return {"full_name": r["full_name"], **scan_dir(dest)}


def main(limit=None):
    TMP.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        with OUT.open() as f:
            done = {s["full_name"] for s in map(json.loads, f) if "error" not in s}
    with REPOS.open() as f:
        repos = [json.loads(line) for line in f]
    todo = [r for r in repos if r["full_name"] not in done][:limit]
    for i, r in enumerate(todo, 1):
        try:
            res = scan_repo(r)
        except (CloneError, subprocess.TimeoutExpired, OSError) as e:  # recorded; retried next run
            res = {"full_name": r["full_name"], "error": f"{type(e).__name__}: {e}"[:300]}
        with OUT.open("a") as f:
            f.write(json.dumps(res) + "\n")
        print(f"[{i}/{len(todo)}] {r['full_name']} {'ERR' if 'error' in res else 'ok'}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
