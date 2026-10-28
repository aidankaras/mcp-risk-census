# MCP Risk Census

A static census of **109 public Model Context Protocol (MCP) servers** on GitHub: what they let an
AI agent do on your machine, and what hygiene protects you. Includes a hand-labeling validation of
the scanner itself — because a census you haven't validated is just pattern matching.

Built by Aidan Karas — Data Science & Mathematics undergraduate, Boston University.

## Headline findings

- **MCP servers are powerful by default.** 65% can run shell commands, 77% write files, 84% make
  outbound network calls (raw scanner counts; validation-adjusted: ~49% / ~59% / ~68%).
- **Protections lag capabilities.** 79% validate tool inputs against a schema, but only 37% restrict
  which filesystem paths they can touch and 36% ship a SECURITY.md.
- **Popularity does not buy hygiene.** Spearman correlation between GitHub stars and hygiene score:
  −0.14 (mean hygiene 2.44 above vs 2.13 below median stars — a small, likely-noise gap).
- **Naive secret scanning is useless.** Of 17 repos flagged for hardcoded API keys, **0 contained a
  real leak** — every hit was a test fixture, AWS's documented example key, or a placeholder. 100%
  false-positive rate without context.
- 59 servers expose a remote (HTTP/SSE) transport; 9 show no auth signal — though the auth heuristic
  is the crudest in this study, so treat that as "worth checking," not a finding.

## Charts

![Capabilities](charts/capabilities.png)
![Hygiene](charts/hygiene.png)
![Popularity vs hygiene](charts/stars_vs_hygiene.png)
![Risk distribution](charts/risk_dist.png)

## Method

1. **Collect** (`collect.py`): GitHub search (topics `mcp-server`, `model-context-protocol`, plus
   TS/Python keyword search); top 250 of 671 unique repos by stars, deduped.
2. **Scan** (`scan.py`): shallow clone → regex counts of capability & hygiene signals → delete clone.
3. **Filter & score** (`analyze.py`): keep actual servers (n = 109). Signals are binary.
   Risk = shell 3 + eval 3 + fs_write 2 + raw SQL 2 + HTTP 1 (0–11).
   Hygiene = SECURITY.md + path guard + input schema + auth signal, −1 for a hardcoded key (−1–4).
4. **Key check** (`keycheck.py`): every hardcoded-key hit manually reviewed with secrets redacted.
5. **Validate** (`dump_sample.py` + `data/hand_labels.json`): 20 repos sampled stratified by stars;
   every capability hit judged in context as real capability vs false positive.

Per-repo data is in `data/servers.jsonl` (public repos; factual signal counts; see caveats).

### Scanner validation

| Signal | Flagged | Truly capable | Precision | Recall |
|---|---|---|---|---|
| shell_exec | 12 | 9 | 0.75 | 1.00 |
| fs_write | 13 | 10 | 0.77 | 1.00 |
| outbound_http | 16 | 14 | 0.81 | 0.93 |
| eval_dynamic | 3 | 1 | 0.33 | 1.00 |
| sql_raw | 1 | 1 | 1.00 | 1.00 |

False positives came overwhelmingly from build scripts, test tooling, bundled frontend code and
comments. `eval_dynamic` is too noisy to publish without a tighter pattern. The reviewers also found
2 capabilities the regex missed (an HTTP tool and raw-SQL connectors with zero hits), so real
capability levels sit slightly *above* the scanner's numbers.

## Reproduce

```bash
python3 -m pip install matplotlib   # only needed for charts.py
python3 collect.py && python3 scan.py && python3 analyze.py && python3 charts.py
```

`scan.py` is resumable and clones are deleted after scanning; nothing is executed in scanned repos.

## Caveats

- Static pattern matching only; "can run shell" ≠ vulnerable. This is **not** a security audit of
  any project, and nothing here alleges a specific project is unsafe.
- Percentages above are pre-validation scanner output; validation-adjusted rates are given where it
  matters. Individual repos are not called out, deliberately — several flagged repos are tools whose
  dangerous capability is their advertised purpose (e.g. security/automation tooling).
- n = 109 of a much larger ecosystem, top-of-search by stars; results describe that sample.

## Skills demonstrated

Data collection at API rate limits, reproducible pipelines, static analysis design, heuristic
scoring, hand-labeling validation (precision/recall), statistical reporting with honest error bars.
