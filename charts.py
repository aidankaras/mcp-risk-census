"""Generate publishable charts from data/servers.jsonl into charts/."""
import json, pathlib, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).parent
rows = [json.loads(l) for l in (ROOT / "data/servers.jsonl").open()]
OUT = ROOT / "charts"; OUT.mkdir(exist_ok=True)

# 1. capability prevalence
caps = ["shell_exec", "fs_write", "outbound_http", "eval_dynamic", "sql_raw"]
hyg = ["input_schema", "auth_mentioned", "path_guard", "security_md"]
labels = ["Run shell commands", "Write files", "Outbound HTTP", "Eval/dynamic code", "Raw SQL"]
fig, ax = plt.subplots(figsize=(8, 4))
vals = [100 * sum(1 for r in rows if r[c]) / len(rows) for c in caps]
ax.barh(labels, vals, color="#c0392b"); ax.invert_yaxis()
ax.set_xlabel("% of servers"); ax.set_title("Dangerous capabilities in 109 public MCP servers")
for i, v in enumerate(vals): ax.text(v + 1, i, f"{v:.0f}%", va="center")
ax.set_xlim(0, 100); fig.tight_layout(); fig.savefig(OUT / "capabilities.png", dpi=150)

# 2. hygiene prevalence
labels2 = ["Validates input schema", "Auth mentioned", "Path guard", "SECURITY.md"]
vals2 = [100 * sum(1 for r in rows if r[c]) / len(rows) for c in hyg]
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(labels2, vals2, color="#27ae60"); ax.invert_yaxis()
for i, v in enumerate(vals2): ax.text(v + 1, i, f"{v:.0f}%", va="center")
ax.set_xlabel("% of servers"); ax.set_xlim(0, 100)
ax.set_title("Protective hygiene in 109 public MCP servers")
fig.tight_layout(); fig.savefig(OUT / "hygiene.png", dpi=150)

# 3. stars vs hygiene scatter (jittered log x)
import random; random.seed(1)
xs = [max(r["stars"], 1) * (1 + random.uniform(-0.15, 0.15)) for r in rows]
ys = [r["hygiene"] + random.uniform(-0.15, 0.15) for r in rows]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.scatter(xs, ys, s=18, alpha=0.6, color="#2c3e50"); ax.set_xscale("log")
ax.set_xlabel("GitHub stars (log, jittered)"); ax.set_ylabel("Hygiene score (−1–4)")
ax.set_title("Popularity does not buy hygiene")
fig.tight_layout(); fig.savefig(OUT / "stars_vs_hygiene.png", dpi=150)

# 4. risk score distribution
fig, ax = plt.subplots(figsize=(7, 4))
rs = [r["risk"] for r in rows]
bins = list(range(0, 13))
ax.hist(rs, bins=bins, color="#8e44ad", edgecolor="white")
ax.set_xlabel("Risk score (0–11)"); ax.set_ylabel("servers")
ax.set_title("Risk score distribution")
ax.axvline(6, ls="--", c="r"); ax.text(6.1, max(ax.get_ylim()) * .9, "high risk", c="r")
fig.tight_layout(); fig.savefig(OUT / "risk_dist.png", dpi=150)
print("charts:", sorted(p.name for p in OUT.glob("*.png")))
