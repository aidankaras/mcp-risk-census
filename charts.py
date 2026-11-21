"""Generate the README charts from data/servers.jsonl and data/summary.json into charts/."""
import json
import pathlib
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter  # noqa: E402

from analyze import HIGH_RISK, read_jsonl  # noqa: E402

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "charts"
CAPS = {"shell_exec": "Run shell commands", "fs_write": "Write files", "outbound_http": "Outbound HTTP",
        "eval_dynamic": "Eval/dynamic code", "sql_raw": "Raw SQL"}
HYG = {"input_schema": "Schema library used", "auth_mentioned": "Auth/API-key keyword",
       "path_guard": "Path guard", "security_md": "SECURITY.md (repo root)"}


def bar_chart(rows, signals, color, title, path):
    vals = [100 * sum(1 for r in rows if r[c]) / len(rows) for c in signals]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(list(signals.values()), vals, color=color)
    ax.invert_yaxis()
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.0f}%", va="center")
    ax.set_xlabel("% of repos (raw scanner flags)")
    ax.set_xlim(0, 100)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    rows = read_jsonl(ROOT / "data/servers.jsonl")
    summary = json.loads((ROOT / "data/summary.json").read_text())
    n = len(rows)
    OUT.mkdir(exist_ok=True)

    bar_chart(rows, CAPS, "#c0392b", f"Capability signals in {n} MCP server repos", OUT / "capabilities.png")
    bar_chart(rows, HYG, "#27ae60", f"Hygiene signals in {n} MCP server repos", OUT / "hygiene.png")

    # stars vs hygiene scatter (jittered, log x)
    rng = random.Random(1)
    xs = [max(r["stars"], 1) * (1 + rng.uniform(-0.15, 0.15)) for r in rows]
    ys = [r["hygiene"] + rng.uniform(-0.15, 0.15) for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(xs, ys, s=18, alpha=0.6, color="#2c3e50")
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([1000, 2000, 5000, 10_000, 20_000, 50_000]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("GitHub stars (log, jittered)")
    ax.set_ylabel("Hygiene score (0–4, jittered)")
    ax.set_title(f"Stars vs hygiene: Spearman ρ = {summary['spearman_stars_hygiene']:.2f}, "
                 f"p = {summary['spearman_stars_hygiene_p']:.2f} (n = {n})")
    fig.tight_layout()
    fig.savefig(OUT / "stars_vs_hygiene.png", dpi=150)
    plt.close(fig)

    # risk score distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist([r["risk"] for r in rows], bins=list(range(0, 13)), color="#8e44ad", edgecolor="white")
    ax.set_xlabel("Risk score (0–11)")
    ax.set_ylabel("repos")
    ax.set_title(f"Risk score distribution (n = {n})")
    ax.axvline(HIGH_RISK, ls="--", c="r")
    ax.text(HIGH_RISK + 1.1, max(ax.get_ylim()) * 0.9, f"risk ≥ {HIGH_RISK}", c="r")
    fig.tight_layout()
    fig.savefig(OUT / "risk_dist.png", dpi=150)
    plt.close(fig)
    print("charts:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
