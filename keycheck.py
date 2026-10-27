"""Re-clone repos flagged hardcoded_key and show each hit's file + redacted context for hand review.
Keys are redacted to their first 6 chars; full secrets are never printed or stored."""
import json, re, subprocess, pathlib, shutil
from scan import HYGIENE, CODE_EXT, TMP

PAT = re.compile(HYGIENE["hardcoded_key"])
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "data" / "keyhits.jsonl"
flagged = [json.loads(l) for l in (ROOT / "data/scan.jsonl").open()]
flagged = [s["full_name"] for s in flagged if s.get("hardcoded_key")]
TMP.mkdir(parents=True, exist_ok=True)
with OUT.open("w") as f:
    for name in flagged:
        d = TMP / name.replace("/", "__")
        shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:limit=300k",
                        f"https://github.com/{name}.git", str(d)], timeout=180)
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix not in CODE_EXT or "node_modules" in p.parts:
                continue
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                for m in PAT.finditer(line):
                    ctx = line.replace(m.group(0), m.group(0)[:6] + "…REDACTED").strip()[:160]
                    f.write(json.dumps({"repo": name, "file": str(p.relative_to(d)), "line": i,
                                        "ctx": ctx}) + "\n")
        shutil.rmtree(d, ignore_errors=True)
        print("done", name, flush=True)
