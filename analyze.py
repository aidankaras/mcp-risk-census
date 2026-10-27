"""Filter to real MCP servers, score risk + hygiene (binary signals), test stars vs hygiene."""
import json, math, pathlib, statistics as st

ROOT = pathlib.Path(__file__).parent
R = {json.loads(l)["full_name"]: json.loads(l) for l in (ROOT / "data/repos.jsonl").open()}
S = [json.loads(l) for l in (ROOT / "data/scan.jsonl").open() if "error" not in l]
EXCLUDE = ("sdk", "framework", "client", "awesome", "list of", "inspector", "tutorial")
RISK_W = {"shell_exec": 3, "eval_dynamic": 3, "fs_write": 2, "sql_raw": 2, "outbound_http": 1}
HYG = ["security_md", "path_guard", "input_schema", "auth_mentioned"]

def is_server(s):
    txt = (s["full_name"] + " " + R[s["full_name"]]["description"]).lower()
    return "mcp" in txt and 0 < s["loc"] < 60000 and not any(w in txt for w in EXCLUDE)

rows = []
for s in filter(is_server, S):
    risk = sum(w for k, w in RISK_W.items() if s[k])              # 0..11
    hyg = sum(1 for k in HYG if s[k]) - (1 if s["hardcoded_key"] else 0)  # -1..4
    rows.append({**s, "stars": R[s["full_name"]]["stars"], "risk": risk, "hygiene": hyg,
                 "remote": bool(s["http_sse"])})

def spearman(x, y):
    rk = lambda v: {i: r for r, i in enumerate(sorted(range(len(v)), key=v.__getitem__))}
    rx, ry = rk(x), rk(y); n = len(x)
    return 1 - 6 * sum((rx[i] - ry[i]) ** 2 for i in range(n)) / (n * (n * n - 1))

n = len(rows)
pct = lambda k: round(100 * sum(1 for r in rows if r[k]) / n)
stars = [r["stars"] for r in rows]; med = st.median(stars)
top = [r["hygiene"] for r in rows if r["stars"] >= med]; bot = [r["hygiene"] for r in rows if r["stars"] < med]
remote_noauth = [r for r in rows if r["remote"] and not r["auth_mentioned"]]
summary = {
    "n_servers": n, "pct": {k: pct(k) for k in [*RISK_W, *HYG, "hardcoded_key", "remote"]},
    "mean_risk": round(st.mean(r["risk"] for r in rows), 2),
    "mean_hygiene": round(st.mean(r["hygiene"] for r in rows), 2),
    "spearman_stars_hygiene": round(spearman(stars, [r["hygiene"] for r in rows]), 3),
    "spearman_stars_risk": round(spearman(stars, [r["risk"] for r in rows]), 3),
    "hygiene_above_median_stars": round(st.mean(top), 2), "hygiene_below_median_stars": round(st.mean(bot), 2),
    "remote_without_auth_signal": len(remote_noauth), "remote_total": sum(r["remote"] for r in rows),
    "high_risk_low_hygiene": sum(1 for r in rows if r["risk"] >= 6 and r["hygiene"] <= 1),
}
(ROOT / "data/servers.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
(ROOT / "data/summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
