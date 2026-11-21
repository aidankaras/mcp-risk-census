import re

from scan import HYGIENE, SIGNALS, TRANSPORT


def hits(table, name, text):
    return len(re.findall(table[name], text))


def test_shell_exec():
    assert hits(SIGNALS, "shell_exec", "subprocess.run(['ls'])")
    assert hits(SIGNALS, "shell_exec", "const { execSync } = require('child_process')")
    assert not hits(SIGNALS, "shell_exec", "print('hello')")


def test_fs_write():
    assert hits(SIGNALS, "fs_write", "fs.writeFileSync(p, data)")
    assert hits(SIGNALS, "fs_write", "with open(path, 'w') as f:")
    assert not hits(SIGNALS, "fs_write", "with open(path) as f:")


def test_outbound_http():
    assert hits(SIGNALS, "outbound_http", "requests.get(url)")
    assert hits(SIGNALS, "outbound_http", "await fetch(url)")
    assert not hits(SIGNALS, "outbound_http", "x = 1")


def test_eval_and_sql():
    assert hits(SIGNALS, "eval_dynamic", "eval(user_input)")
    assert hits(SIGNALS, "sql_raw", 'cur.execute(f"SELECT * FROM t WHERE id={i}")')
    assert not hits(SIGNALS, "sql_raw", 'cur.execute("SELECT * FROM t WHERE id=?", (i,))')


def test_hygiene():
    assert hits(HYGIENE, "path_guard", "if not p.is_relative_to(root):")
    assert hits(HYGIENE, "input_schema", "inputSchema: z.object({})")
    assert not hits(HYGIENE, "path_guard", "x = 1")


def test_auth_and_transport():
    assert hits(HYGIENE, "auth_mentioned", 'headers["Authorization"] = token')
    assert hits(HYGIENE, "auth_mentioned", "api_key = os.environ['X']")
    assert not hits(HYGIENE, "auth_mentioned", "author = 'me'")
    assert hits(TRANSPORT, "http_sse", "new SSEServerTransport('/messages', res)")
    assert hits(TRANSPORT, "http_sse", "mcp.run(transport='streamable-http')")
    assert not hits(TRANSPORT, "http_sse", "new StdioServerTransport()")


def test_hardcoded_key_shapes():
    # Built at runtime so this file holds no secret-shaped literals.
    assert hits(HYGIENE, "hardcoded_key", "k = '" + "ghp_" + "x" * 36 + "'")
    assert hits(HYGIENE, "hardcoded_key", "k = '" + "AKIA" + "Z" * 16 + "'")
    assert not hits(HYGIENE, "hardcoded_key", "k = 'sk-short'")
