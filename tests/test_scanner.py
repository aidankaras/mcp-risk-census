from keycheck import PAT, key_hits, redact
from scan import ALL_PATTERNS, find_matches, iter_code_files, scan_dir

# Built at runtime so this file holds no secret-shaped literals.
FAKE_OPENAI = "sk-" + "a1" * 12
FAKE_AWS = "AKIA" + "B" * 16


def test_redact_every_key_on_a_line():
    line = f"key1={FAKE_OPENAI} and key2={FAKE_AWS}"
    out = redact(line)
    assert not PAT.search(out)
    assert out == "key1=sk-a1a…REDACTED and key2=AKIABB…REDACTED"


def test_find_matches_reports_start_line_of_multiline_match():
    text = "line one\nconst r = await db.query(`SELECT *\n  FROM t WHERE id = ${id}`);\n"
    hits = [(name, ln) for name, ln, _ in find_matches(text, {"sql_raw": ALL_PATTERNS["sql_raw"]})]
    assert hits == [("sql_raw", 2)]


def test_iter_code_files_skips_dirs_and_extensions(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "server.ts").write_text("x")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "server.test.ts").write_text("x")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("x")
    (tmp_path / "README.md").write_text("x")
    assert [str(rel) for _, rel in iter_code_files(tmp_path)] == ["src/server.ts"]


def test_scan_dir_and_key_hits_agree(tmp_path):
    (tmp_path / "server.py").write_text(f"import subprocess\nsubprocess.run(['ls'])\nK = '{FAKE_AWS}'\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(f"K = '{FAKE_OPENAI}'\n")
    (tmp_path / "SECURITY.md").write_text("report privately")
    counts = scan_dir(tmp_path)
    assert counts["shell_exec"] == 1
    assert counts["hardcoded_key"] == 1
    assert counts["security_md"] is True
    hits = list(key_hits(tmp_path))
    assert hits == [{"file": "server.py", "line": 3, "ctx": "K = 'AKIABB…REDACTED'"}]


def test_security_md_found_in_github_dir(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "SECURITY.md").write_text("x")
    assert scan_dir(tmp_path)["security_md"] is True
    (tmp_path / ".github" / "SECURITY.md").unlink()
    assert scan_dir(tmp_path)["security_md"] is False


def test_tsx_files_are_scanned(tmp_path):
    (tmp_path / "App.tsx").write_text("await fetch(url)\n")
    assert scan_dir(tmp_path)["outbound_http"] == 1
