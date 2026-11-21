import json

import collect


def test_refresh_stars_updates_only_stars(tmp_path, monkeypatch):
    fake_gh = tmp_path / "gh"
    fake_gh.write_text('#!/bin/sh\ncase "$2" in repos/a/ok) echo 42 ;; *) exit 1 ;; esac\n')
    fake_gh.chmod(0o755)
    monkeypatch.setattr(collect, "GH", str(fake_gh))
    path = tmp_path / "repos.jsonl"
    path.write_text(json.dumps({"full_name": "a/ok", "stars": 1, "description": "d"}) + "\n"
                    + json.dumps({"full_name": "a/gone", "stars": 7, "description": "e"}) + "\n")
    collect.refresh_stars(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows == [{"full_name": "a/ok", "stars": 42, "description": "d", "stars_refreshed": True},
                    {"full_name": "a/gone", "stars": 7, "description": "e", "stars_refreshed": False}]
