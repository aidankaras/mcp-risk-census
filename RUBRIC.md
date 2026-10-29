# MCP Risk Census — scoring rubric 

Goal: a reproducible, publishable data study of ~200 public MCP servers:
what capabilities they expose to an AI agent, and what hygiene protects users.

## What scan.py measures (static regex heuristics — counts, not proof)
Capabilities (risk surface): shell_exec, fs_write, outbound_http, eval_dynamic, sql_raw
Hygiene (mitigations): env_secrets, hardcoded_key, auth_mentioned, path_guard, input_schema, SECURITY.md
Transport: stdio vs http/sse (remote servers = network exposure)

## Open decisions
1. Weights: how much should shell_exec count vs outbound_http? (proposal: shell 3, eval 3, fs_write 2, http 1, sql_raw 2)
2. Mitigation credit: does path_guard / input_schema offset capability risk, or score separately?
3. Binary vs count: "has shell exec at all" (cleaner) or density per 1k LOC?
4. Validation: hand-label ~20 repos to measure false-positive rate of the regexes (this is the DS-credible part).
5. Questions the write-up answers, e.g. "Do popular servers have better hygiene than obscure ones?" (stars vs score), "How many remote servers ship without auth?"

## Caveats to publish
Static heuristics only; no code is executed; counts include false positives; not a security audit of any project.
