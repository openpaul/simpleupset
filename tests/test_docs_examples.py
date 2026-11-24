"""Keep the hand-written tables in docs/examples.rst honest."""

import pytest

from simpleupset import UpSet, from_memberships

ITEMS = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}


def check(data, expected_subsets, expected_totals, **kwargs):
    upset = UpSet(data, **kwargs)
    assert {"".join(sorted(s.categories)) if s.categories else "": s.size
            for s in upset.subsets} == expected_subsets
    assert upset.totals == expected_totals


def test_two_sets():
    check({"a": {1, 2, 3}, "b": {3, 4}}, {"a": 2, "b": 1, "ab": 1}, {"a": 3, "b": 2})


def test_dict_of_lists():
    check(
        ITEMS,
        {"ab": 2, "bc": 2, "a": 1, "b": 1, "c": 1, "ac": 1},
        {"b": 5, "a": 4, "c": 4},
    )
    assert UpSet(ITEMS).data.categories == ["b", "a", "c"]


def test_nested_sets():
    sets = {"all": [1, 2, 3, 4, 5, 6], "even": [2, 4, 6], "small": [1, 2]}
    upset = UpSet(sets, show_percentages=True)
    sizes = {frozenset(s.categories): s.size for s in upset.subsets}
    assert sizes == {
        frozenset({"all"}): 2,
        frozenset({"all", "even"}): 2,
        frozenset({"all", "small"}): 1,
        frozenset({"all", "even", "small"}): 1,
    }
    assert upset.totals == {"all": 6, "even": 3, "small": 2}


def test_filtering():
    check(ITEMS, {"ab": 2, "ac": 1, "bc": 2}, {"b": 5, "a": 4, "c": 4}, min_degree=2)


def test_weighted():
    data = from_memberships([["x"], ["x", "y"], ["y"], ["x"]], data=[1.5, 2.0, 4.0, 0.5])
    check(data, {"x": 2, "y": 4, "xy": 2}, {"x": 4, "y": 6})


def test_legacy_series():
    pd = pytest.importorskip("pandas")
    index = pd.MultiIndex.from_tuples(
        [(True, False), (True, True), (False, True)], names=["cat1", "cat2"]
    )
    upset = UpSet(pd.Series([5, 3, 2], index=index))
    assert {frozenset(s.categories): s.size for s in upset.subsets} == {
        frozenset({"cat1"}): 5,
        frozenset({"cat1", "cat2"}): 3,
        frozenset({"cat2"}): 2,
    }
    assert upset.totals == {"cat1": 8, "cat2": 5}
