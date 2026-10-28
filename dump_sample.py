"""Sample 20 servers (stratified by stars), dump every capability-signal match with context
for human/AI hand-labeling. Output: data/label_dump.jsonl"""
import json, re, random, subprocess, pathlib, shutil
from scan import SIGNALS, CODE_EXT, SKIP_DIRS, TMP

ROOT = pathlib.Path(__file__).parent
rows = [json.loads(l) for l in (ROOT / "data/servers.jsonl").open()]
rows.sort(key=lambda r: -r["stars"])
# stratified sample: 7 from top third, 7 middle, 6 bottom
thirds = [rows[:36], rows[36:73], rows[73:]]
random.seed(7)
sample = [r for t in thirds for r in random.sample(t, min(len(t), 7))][:20]
TMP.mkdir(parents=True, exist_ok=True)
OUT = (ROOT / "data/label_dump.jsonl").open("w")
pats = {k: re.compile(p) for k, p in SIGNALS.items()}
for r in sample:
    d = TMP / r["full_name"].replace("/", "__")
    shutil.rmtree(d, ignore_errors=True)
    if subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:limit=300k",
                       f"https://github.com/{r['full_name']}.git", str(d)],
                      timeout=180).returncode != 0:
        continue
    hits = []
    for p in d.rglob("*"):
        if not p.is_file() or p.suffix not in CODE_EXT or set(p.relative_to(d).parts) & SKIP_DIRS:
            continue
        lines = p.read_text(errors="ignore").splitlines()
        for i, line in enumerate(lines, 1):
            for k, pat in pats.items():
                m = pat.search(line)
                if m:
                    hits.append({"sig": k, "file": str(p.relative_to(d))[:90], "line": i,
                                 "ctx": line.strip()[:160]})
    shutil.rmtree(d, ignore_errors=True)
    # cap context for readability: 25 per signal
    out = {"repo": r["full_name"], "stars": r["stars"], "loc": r["loc"],
           "hits": {k: [h for h in hits if h["sig"] == k][:25] for k in SIGNALS}}
    OUT.write(json.dumps(out) + "\n")
    print("dumped", r["full_name"], len(hits), flush=True)
OUT.close()
