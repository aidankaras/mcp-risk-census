# MCP Risk Census (draft, unpublished)

A static census of public Model Context Protocol (MCP) server repos on GitHub: what they let an
AI agent do on your machine, and what hygiene protects you.

## Method
1. `collect.py`: GitHub search (topics `mcp-server`, `model-context-protocol`, plus keyword search
   for TS/Python), top 250 of 671 unique repos by stars.
2. `scan.py`: shallow clone, regex counts of capability and hygiene signals; test/example dirs skipped.
3. `analyze.py`: keeps only actual servers ("mcp" in name/description, <60k LOC, no SDK/framework/client) → **n = 109**.
   Signals are binary (present / absent). Risk = shell 3 + eval 3 + fs_write 2 + raw SQL 2 + http 1 (0–11).
   Hygiene = SECURITY.md + path guard + input schema + auth mention, −1 for a hardcoded key (−1–4).
4. `keycheck.py`: hand review of every hardcoded-key hit (keys redacted).

## First results (n = 109, unvalidated heuristics)
- 65% can run shell commands, 77% write files, 84% make outbound HTTP calls, 16% use eval-style dynamic code.
- 79% validate tool inputs with a schema; only 37% guard file paths; 36% have SECURITY.md.
- 59 expose an HTTP/SSE transport; 9 of those show no auth signal at all.
- 8 servers score high-risk (≥6) with low hygiene (≤1).
- **Popularity doesn't buy hygiene:** Spearman(stars, hygiene) = −0.14; mean hygiene 2.44 above vs
  2.13 below median stars (small, likely noise).
- **Hardcoded keys: 0 real leaks out of 17 flagged repos.** All 197 hits were test fixtures, AWS's documented
  example key, placeholders (`ghp_xxx`, `sk-1234…`) or minified binary. The regex's false-positive rate on this sample was 100%:
  naive secret scanning is close to useless without context.

## Validation (hand-labeling, n = 20 stratified repos)
Two independent reviewers judged every regex hit in production code as a real capability or false positive.
| Signal | Flagged | Truly capable | Precision | Recall |
|---|---|---|---|---|
| shell_exec | 12 | 9 | 0.75 | 1.00 |
| fs_write | 13 | 10 | 0.77 | 1.00 |
| outbound_http | 16 | 14 | 0.81 | 0.93 |
| eval_dynamic | 3 | 1 | 0.33 | 1.00 |
| sql_raw | 1 | 1 | 1.00 | 1.00 |
False positives were overwhelmingly build scripts, test tooling, bundled frontend code and comments;
eval_dynamic is too noisy to publish without a tightened pattern. Reviewers also caught 2 regex misses
(an HTTP tool and raw-SQL connectors with 0 hits), so real capability levels are slightly higher than
the scanner reports.

## Caveats
Static pattern matching only; nothing executed. "Can run shell" ≠ vulnerable. Not a security audit
of any project. Capability percentages are pre-validation scanner output; applying measured precision
would put real rates at roughly: shell ~49%, fs_write ~59%, HTTP ~68%.
