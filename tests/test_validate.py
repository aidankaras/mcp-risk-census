import pytest

from validate import confusion, wilson


def test_wilson_matches_known_interval():
    # 9/12: Wilson 95% interval is about 0.468-0.911
    assert wilson(9, 12) == [0.47, 0.91]
    assert wilson(1, 1) == [0.21, 1.0]
    assert wilson(0, 0) is None


def test_confusion_counts():
    items = [{"flag": {"s": True}, "label": {"s": True}},
             {"flag": {"s": True}, "label": {"s": False}},
             {"flag": {"s": False}, "label": {"s": True}}]
    assert confusion(items, "s") == (2, 2, 1)


def test_wilson_bounds():
    lo, hi = wilson(3, 3)
    assert 0 < lo < 1 and hi == pytest.approx(1.0)
