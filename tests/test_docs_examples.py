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


def test_non_string_categories():
    upset = UpSet({2020: ["a", "b", "c"], 2021: ["b", "c", "d"]})
    assert {frozenset(s.categories): s.size for s in upset.subsets} == {
        frozenset({2020}): 1,
        frozenset({2020, 2021}): 2,
        frozenset({2021}): 1,
    }
    assert upset.totals == {2020: 3, 2021: 3}


def test_precomputed_counts():
    data = from_memberships(
        [["a"], ["b"], ["c"], ["a", "b"], ["a", "b", "c"]], data=[10, 5, 4, 3, 2]
    )
    check(data, {"a": 10, "b": 5, "c": 4, "ab": 3, "abc": 2}, {"a": 15, "b": 10, "c": 6})


def test_stacked_bars():
    genes = {"liver": ["g1", "g2", "g3", "g4"], "brain": ["g3", "g4", "g5", "g6"]}
    kind = {"g1": "coding", "g2": "non-coding", "g3": "coding",
            "g4": "coding", "g5": "non-coding", "g6": "coding"}
    upset = UpSet(genes, stack_by=kind)
    st = upset.stacked
    assert st.groups == ["coding", "non-coding"]
    split = {frozenset(s.categories): st.subsets[i].tolist() for i, s in enumerate(upset.subsets)}
    assert split == {
        frozenset({"liver"}): [1, 1],
        frozenset({"brain"}): [1, 1],
        frozenset({"liver", "brain"}): [2, 0],
    }
    assert dict(zip(upset.data.categories, st.totals.tolist())) == {
        "liver": [3, 1],
        "brain": [3, 1],
    }
