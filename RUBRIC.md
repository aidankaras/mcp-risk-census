# MCP Risk Census — scoring rubric

Goal: a reproducible data study of public MCP servers: what capabilities they expose to an AI
agent, and what hygiene protects users. Collection kept the top 250 candidate repos by stars;
the server filter in `analyze.py` left 109.

## What scan.py measures (static regex heuristics — counts, not proof)

Capabilities (risk surface): shell_exec, fs_write, outbound_http, eval_dynamic, sql_raw
Hygiene (mitigations): auth_mentioned, path_guard, input_schema, SECURITY.md; hardcoded_key is
recorded but not scored
Transport: http/sse (remote servers = network exposure)

## Decisions taken

1. Weights: shell 3, eval 3, fs_write 2, raw SQL 2, outbound HTTP 1 (risk 0–11).
2. Mitigations are scored separately as hygiene (0–4), not subtracted from risk.
3. Binary signals ("has shell exec at all"), not density per 1k LOC.
4. Validation: 20 repos sampled stratified by stars, each labeled per signal as really capable or
   not (LLM labels; see README). Precision/recall with Wilson intervals in `validate.py`.
5. Questions the write-up answers: do popular servers have better hygiene (Spearman, stars vs
   hygiene)? How many remote servers show no auth signal?
6. Server filter: name/description mentions MCP, none of the EXCLUDE words in `analyze.py`, and
   1–59,999 LOC. The LOC cut-off and the high-risk thresholds (risk ≥ 6, hygiene ≤ 1) were picked
   by hand, not tuned. The filter keeps some non-servers; see `data/likely_non_servers.json`.
7. The −1 hygiene penalty for a hardcoded key was dropped after manual review found no live
   credential among the key matches.

## Versions

- **v1**: `scan.py` at commit `515fada`. Produced `data/scan.jsonl` and every published number.
  The monthly rescan (`.github/workflows/rescan.yml`) is pinned to it.
- **v2** (current `scan.py`): SECURITY.md is also found in `.github/` and `docs/`; `.tsx`, `.jsx`,
  `.cjs`, `.mts`, `.cts`, `.kt`, `.swift` files are scanned; the unused `env_secrets` and `stdio`
  signals are removed. Not yet applied to the published data.

Open: `auth_mentioned` mostly matches outbound API keys, not inbound authentication; it needs a
narrower, validated pattern before the next baseline.

## Caveats to publish

Static heuristics only; no code is executed; counts include false positives; not a security audit
of any project.
