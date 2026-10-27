"""Step 2: static first-pass scan of each repo (shallow clone, regex signals, delete clone).

Signals are DRAFT heuristics, not verdicts -- the rubric (RUBRIC.md) is Aidan's to finalize.
Appends to data/scan.jsonl; resumable (skips repos already scanned).
Light on purpose: VPS has 1 vCPU, so clones are depth-1, blob-filtered, one at a time.
"""
import json, re, subprocess, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).parent
REPOS = ROOT / "data" / "repos.jsonl"
OUT = ROOT / "data" / "scan.jsonl"
TMP = pathlib.Path("/opt/data/cache/scratch/mcp-census-clones")
CODE_EXT = {".py", ".ts", ".js", ".mjs", ".go", ".rs", ".java", ".cs", ".rb"}
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
    "env_secrets": r"(process\.env\.|os\.environ|os\.getenv|Getenv\()",
    "hardcoded_key": r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[0-9A-Za-z-]{20,})",
    "auth_mentioned": r"\b(oauth|OAuth|bearer|Authorization|api[_-]?key)\b",
    "path_guard": r"(allowed_?dir|allowedDirectories|realpath|path\.resolve\(.*startsWith|is_relative_to)",
    "input_schema": r"(zod|z\.object|inputSchema|pydantic|BaseModel)",
}
TRANSPORT = {"stdio": r"stdio", "http_sse": r"(\bSSE\b|\bsse\b|SSEServerTransport|StreamableHTTP|streamable-http)"}


def scan_repo(r):
    dest = TMP / r["full_name"].replace("/", "__")
    shutil.rmtree(dest, ignore_errors=True)
    cl = subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:limit=300k",
                         f"https://github.com/{r['full_name']}.git", str(dest)],
                        capture_output=True, text=True, timeout=180)
    if cl.returncode != 0:
        return {"full_name": r["full_name"], "error": cl.stderr[-300:]}
    counts = {k: 0 for k in (*SIGNALS, *HYGIENE, *TRANSPORT)}
    n_files = loc = 0
    has_security_md = any(p.name.upper() == "SECURITY.MD" for p in dest.glob("*"))
    for p in dest.rglob("*"):
        if not p.is_file() or p.suffix not in CODE_EXT or set(p.relative_to(dest).parts) & SKIP_DIRS:
            continue
        try:
            txt = p.read_text(errors="ignore")
        except OSError:
            continue
        n_files += 1
        loc += txt.count("\n")
        for d in (SIGNALS, HYGIENE, TRANSPORT):
            for k, pat in d.items():
                counts[k] += len(re.findall(pat, txt))
    shutil.rmtree(dest, ignore_errors=True)
    return {"full_name": r["full_name"], "code_files": n_files, "loc": loc,
            "security_md": has_security_md, **counts}


def main(limit=None):
    TMP.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {json.loads(l)["full_name"] for l in OUT.open()}
    repos = [json.loads(l) for l in REPOS.open()]
    todo = [r for r in repos if r["full_name"] not in done][:limit]
    for i, r in enumerate(todo, 1):
        try:
            res = scan_repo(r)
        except Exception as e:  # keep going; record failure
            res = {"full_name": r["full_name"], "error": str(e)[:300]}
        with OUT.open("a") as f:
            f.write(json.dumps(res) + "\n")
        print(f"[{i}/{len(todo)}] {r['full_name']} {'ERR' if 'error' in res else 'ok'}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
