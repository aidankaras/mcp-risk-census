from snapshot_diff import rows


def test_rows_compares_shared_numeric_fields():
    base = {"n": 109, "pct": {"shell": 65}, "label": "x", "flag": True}
    snap = {"n": 112, "pct": {"shell": 61}, "label": "y", "flag": False}
    assert list(rows(base, snap)) == [("n", 109, 112), ("pct.shell", 65, 61)]
