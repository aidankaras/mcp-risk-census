import pytest

from analyze import is_server, score, spearman


def average_ranks(v):
    order = sorted(range(len(v)), key=v.__getitem__)
    ranks = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb)


def test_spearman_handles_ties_in_sorted_input():
    # Rows arrive sorted by stars (descending) and hygiene is a small integer with many ties.
    # Ranking by sort position (no tie handling) gave -0.45 here; the correct value is +0.52.
    stars = [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]
    hygiene = [2, 2, 2, 2, 2, 2, 2, 2, 2, 1]
    rho, p = spearman(stars, hygiene)
    assert rho == pytest.approx(pearson(average_ranks(stars), average_ranks(hygiene)))
    assert rho == pytest.approx(0.5222, abs=1e-4)
    assert 0 <= p <= 1


def test_score_weights():
    repos = {"a/b": {"stars": 5, "description": "mcp server"}}
    s = {"full_name": "a/b", "shell_exec": 4, "eval_dynamic": 0, "fs_write": 1, "sql_raw": 0,
         "outbound_http": 2, "security_md": True, "path_guard": 0, "input_schema": 3,
         "auth_mentioned": 0, "hardcoded_key": 0, "http_sse": 1}
    r = score(s, repos)
    assert r["risk"] == 3 + 2 + 1
    assert r["hygiene"] == 2
    assert r["remote"] is True


def test_is_server_keyword_and_loc_filter():
    repos = {"x/mcp-thing": {"description": "an MCP server"},
             "x/mcp-sdk": {"description": "Python SDK for MCP"},
             "x/other": {"description": "a web app"}}
    assert is_server({"full_name": "x/mcp-thing", "loc": 500}, repos)
    assert not is_server({"full_name": "x/mcp-thing", "loc": 0}, repos)
    assert not is_server({"full_name": "x/mcp-thing", "loc": 70_000}, repos)
    assert not is_server({"full_name": "x/mcp-sdk", "loc": 500}, repos)
    assert not is_server({"full_name": "x/other", "loc": 500}, repos)
