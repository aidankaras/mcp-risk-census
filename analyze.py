"""Filter to MCP server repos, score risk + hygiene (binary signals), test stars vs hygiene."""
import json
import pathlib
import statistics as st

from scipy.stats import spearmanr

ROOT = pathlib.Path(__file__).parent
EXCLUDE = ("sdk", "framework", "client", "awesome", "list of", "inspector", "tutorial")
# Upper LOC bound picked by hand when the filter was built, to drop very large repos
# (SDKs, monorepos, full apps). Not tuned; see RUBRIC.md.
MAX_LOC = 60_000
RISK_W = {"shell_exec": 3, "eval_dynamic": 3, "fs_write": 2, "sql_raw": 2, "outbound_http": 1}
HYGIENE_SIGNALS = ["security_md", "path_guard", "input_schema", "auth_mentioned"]
# Cut-offs for the high_risk_low_hygiene count, picked by hand. Risk 6 is reached by e.g.
# shell + eval, or shell + file write + HTTP.
HIGH_RISK = 6
LOW_HYGIENE = 1


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_repos(path=ROOT / "data/repos.jsonl"):
    return {r["full_name"]: r for r in read_jsonl(path)}


def load_scan(path=ROOT / "data/scan.jsonl"):
    """Scan rows without errors; if a repo was scanned more than once, the last good row wins."""
    rows = {}
    for s in read_jsonl(path):
        if "error" not in s:
            rows[s["full_name"]] = s
    return list(rows.values())


def is_server(s, repos):
    txt = (s["full_name"] + " " + repos[s["full_name"]]["description"]).lower()
    return "mcp" in txt and 0 < s["loc"] < MAX_LOC and not any(w in txt for w in EXCLUDE)


def score(s, repos):
    risk = sum(w for k, w in RISK_W.items() if s[k])                      # 0..11
    hyg = sum(1 for k in HYGIENE_SIGNALS if s[k])                         # 0..4
    return {**s, "stars": repos[s["full_name"]]["stars"], "risk": risk, "hygiene": hyg,
            "remote": bool(s["http_sse"])}


def spearman(x, y):
    """Spearman rho and two-sided p-value; ties get average ranks (scores are small integers)."""
    res = spearmanr(x, y)
    return float(res.statistic), float(res.pvalue)


def summarize(rows):
    n = len(rows)

    def pct(k):
        return round(100 * sum(1 for r in rows if r[k]) / n)

    stars = [r["stars"] for r in rows]
    med = st.median(stars)
    top = [r["hygiene"] for r in rows if r["stars"] >= med]
    bot = [r["hygiene"] for r in rows if r["stars"] < med]
    rho_h, p_h = spearman(stars, [r["hygiene"] for r in rows])
    rho_r, p_r = spearman(stars, [r["risk"] for r in rows])
    return {
        "n_servers": n, "pct": {k: pct(k) for k in [*RISK_W, *HYGIENE_SIGNALS, "hardcoded_key", "remote"]},
        "mean_risk": round(st.mean(r["risk"] for r in rows), 2),
        "mean_hygiene": round(st.mean(r["hygiene"] for r in rows), 2),
        "spearman_stars_hygiene": round(rho_h, 3), "spearman_stars_hygiene_p": round(p_h, 3),
        "spearman_stars_risk": round(rho_r, 3), "spearman_stars_risk_p": round(p_r, 3),
        "hygiene_above_median_stars": round(st.mean(top), 2),
        "hygiene_below_median_stars": round(st.mean(bot), 2),
        "remote_without_auth_signal": sum(1 for r in rows if r["remote"] and not r["auth_mentioned"]),
        "remote_total": sum(r["remote"] for r in rows),
        "high_risk_low_hygiene": sum(1 for r in rows if r["risk"] >= HIGH_RISK and r["hygiene"] <= LOW_HYGIENE),
    }


def load_likely_non_servers(path=ROOT / "data/likely_non_servers.json"):
    with open(path) as f:
        return set(json.load(f)["repos"])


def main():
    repos = load_repos()
    rows = [score(s, repos) for s in load_scan() if is_server(s, repos)]
    summary = summarize(rows)
    # Sensitivity check: the keyword filter keeps some repos that are not servers.
    non_servers = load_likely_non_servers()
    sub = summarize([r for r in rows if r["full_name"] not in non_servers])
    summary["excluding_likely_non_servers"] = {
        k: sub[k] for k in ("n_servers", "pct", "spearman_stars_hygiene", "spearman_stars_hygiene_p",
                            "remote_without_auth_signal", "remote_total")}
    (ROOT / "data/servers.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (ROOT / "data/summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
