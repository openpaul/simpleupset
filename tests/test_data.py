import numpy as np
import pytest

from simpleupset import UpSetData, from_contents, from_indicators, from_memberships
from simpleupset.data import to_upset_data


def sizes(subsets):
    return {s.categories: s.size for s in subsets}


@pytest.fixture
def contents():
    return {"a": {1, 2, 3, 4}, "b": {3, 4, 5}, "c": {4, 6}}


def test_from_contents_exclusive_intersections(contents):
    data = from_contents(contents)
    assert data.categories == ["a", "b", "c"]
    assert data.membership.shape == (6, 3)
    assert sizes(data.subsets()) == {
        frozenset("a"): 2,  # 1, 2
        frozenset("ab"): 1,  # 3
        frozenset("abc"): 1,  # 4
        frozenset("b"): 1,  # 5
        frozenset("c"): 1,  # 6
    }


def test_category_totals(contents):
    assert from_contents(contents).category_totals() == {"a": 4, "b": 3, "c": 2}


def test_from_contents_rejects_string_values():
    with pytest.raises(TypeError, match="string"):
        from_contents({"a": "abc"})


def test_from_contents_accepts_lists_and_duplicates():
    data = from_contents({"a": [1, 1, 2], "b": [2]})
    assert sizes(data.subsets()) == {frozenset("a"): 1, frozenset("ab"): 1}


def test_from_contents_empty():
    data = from_contents({"a": set(), "b": set()})
    assert data.subsets() == []
    assert data.category_totals() == {"a": 0, "b": 0}


def test_from_memberships_with_weights():
    data = from_memberships([["a"], ["a", "b"], ["a"], []], data=[1.5, 2, 3, 4])
    assert data.categories == ["a", "b"]
    assert sizes(data.subsets()) == {
        frozenset("a"): 4.5,
        frozenset("ab"): 2,
        frozenset(): 4,
    }
    assert [s.count for s in data.subsets(sort_by="input")] == [2, 1, 1]


def test_from_indicators_dict():
    data = from_indicators({"x": [True, False, True], "y": [True, True, False]})
    assert sizes(data.subsets()) == {frozenset("xy"): 1, frozenset("y"): 1, frozenset("x"): 1}


def test_sort_by_cardinality_and_input(contents):
    data = from_contents(contents)
    assert data.subsets(sort_by="cardinality")[0].categories == frozenset("a")
    assert data.subsets(sort_by="-cardinality")[-1].categories == frozenset("a")
    assert [s.categories for s in data.subsets(sort_by="input")] == [
        frozenset("a"),
        frozenset("ab"),
        frozenset("abc"),
        frozenset("b"),
        frozenset("c"),
    ]


def test_sort_by_degree(contents):
    order = [s.categories for s in from_contents(contents).subsets(sort_by="degree")]
    assert order == [
        frozenset("a"),
        frozenset("b"),
        frozenset("c"),
        frozenset("ab"),
        frozenset("abc"),
    ]
    rev = [s.categories for s in from_contents(contents).subsets(sort_by="-degree")]
    assert rev == order[::-1]


def test_invalid_sort_by(contents):
    with pytest.raises(ValueError, match="sort_by"):
        from_contents(contents).subsets(sort_by="nope")


def test_filters(contents):
    data = from_contents(contents)
    assert set(sizes(data.subsets(min_degree=2))) == {frozenset("ab"), frozenset("abc")}
    assert set(sizes(data.subsets(max_degree=1))) == {frozenset("a"), frozenset("b"), frozenset("c")}
    assert set(sizes(data.subsets(min_subset_size=2))) == {frozenset("a")}
    assert frozenset("a") not in sizes(data.subsets(max_subset_size=1))


def test_include_empty_subsets():
    data = from_contents({"a": {1}, "b": {2}})
    subs = data.subsets(include_empty_subsets=True)
    assert len(subs) == 4
    assert sizes(subs)[frozenset("ab")] == 0


def test_sort_categories(contents):
    data = from_contents({"small": {1}, "big": {1, 2, 3}, "mid": {2, 3}})
    assert data.sort_categories("cardinality").categories == ["big", "mid", "small"]
    assert data.sort_categories("-cardinality").categories == ["small", "mid", "big"]
    assert data.sort_categories("input").categories == ["small", "big", "mid"]
    assert data.sort_categories("-input").categories == ["mid", "big", "small"]
    sorted_data = data.sort_categories("cardinality")
    assert sizes(sorted_data.subsets()) == sizes(data.subsets())


def test_upsetdata_validation():
    with pytest.raises(ValueError, match="shape"):
        UpSetData(["a", "b"], np.zeros((3, 1), dtype=bool))
    with pytest.raises(ValueError, match="duplicate category 'a'$"):
        UpSetData(["a", "a"], np.zeros((3, 2), dtype=bool))
    with pytest.raises(ValueError, match="weights"):
        UpSetData(["a"], np.zeros((3, 1), dtype=bool), [1, 2])


def test_to_upset_data_rejects_unknown():
    with pytest.raises(TypeError):
        to_upset_data([1, 2, 3])


# ------------------------------------------------------------- legacy pandas


def test_legacy_series_with_boolean_multiindex():
    pd = pytest.importorskip("pandas")
    idx = pd.MultiIndex.from_tuples(
        [(True, False), (True, True), (False, True)], names=["cat1", "cat2"]
    )
    series = pd.Series([5, 3, 2], index=idx)
    data = to_upset_data(series)  # unique index -> sum of values
    assert data.categories == ["cat1", "cat2"]
    assert sizes(data.subsets()) == {
        frozenset({"cat1"}): 5,
        frozenset({"cat1", "cat2"}): 3,
        frozenset({"cat2"}): 2,
    }


def test_legacy_series_with_duplicates_counts():
    pd = pytest.importorskip("pandas")
    idx = pd.MultiIndex.from_tuples(
        [(True, False), (True, False), (False, True)], names=["a", "b"]
    )
    data = to_upset_data(pd.Series([10.0, 20.0, 30.0], index=idx))
    assert sizes(data.subsets()) == {frozenset("a"): 2, frozenset("b"): 1}


def test_legacy_dataframe_sum_over():
    pd = pytest.importorskip("pandas")
    idx = pd.MultiIndex.from_tuples(
        [(True, False), (True, False), (False, True)], names=["a", "b"]
    )
    df = pd.DataFrame({"value": [1.0, 2.0, 4.0]}, index=idx)
    assert sizes(to_upset_data(df).subsets()) == {frozenset("a"): 2, frozenset("b"): 1}
    summed = to_upset_data(df, sum_over="value")
    assert sizes(summed.subsets()) == {frozenset("a"): 3, frozenset("b"): 4}


def test_legacy_upsetplot_from_contents_output_shape():
    """Mimic upsetplot.from_contents: DataFrame with bool index and an 'id' column."""
    pd = pytest.importorskip("pandas")
    idx = pd.MultiIndex.from_tuples(
        [(True, False), (True, True), (False, True)], names=["a", "b"]
    )
    df = pd.DataFrame({"id": ["x", "y", "z"]}, index=idx)
    assert sizes(to_upset_data(df).subsets()) == {
        frozenset("a"): 1,
        frozenset("ab"): 1,
        frozenset("b"): 1,
    }


def test_from_indicators_dataframe():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": [True, False], "b": [True, True]})
    assert sizes(from_indicators(df).subsets()) == {frozenset("ab"): 1, frozenset("b"): 1}


def test_dict_of_lists_input():
    items = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
    data = from_contents(items)
    assert sizes(data.subsets()) == {
        frozenset("a"): 1,  # 1
        frozenset("ab"): 2,  # 2, 3
        frozenset("ac"): 1,  # 4
        frozenset("bc"): 2,  # 5, 21
        frozenset("b"): 1,  # 19
        frozenset("c"): 1,  # 30
    }


# ------------------------------------------------------- category name types


def test_int_categories_round_trip():
    data = from_contents({1: [1, 2], 2: [2, 3]})
    assert data.categories == [1, 2]
    assert data.category_totals() == {1: 2, 2: 2}
    assert sizes(data.subsets()) == {frozenset({1}): 1, frozenset({2}): 1, frozenset({1, 2}): 1}
    assert data.labels == ["1", "2"]


@pytest.mark.parametrize("names", [[0.5, 1.5], [("x", 1), ("y", 2)], [None, "b"]])
def test_other_hashable_categories(names):
    data = from_contents({names[0]: [1, 2], names[1]: [2]})
    assert data.categories == names
    assert data.labels == [str(n) for n in names]


def test_mixed_int_and_str_with_distinct_labels():
    data = from_contents({1: [1], "b": [1, 2]})
    assert data.category_totals() == {1: 1, "b": 2}


def test_same_label_raises():
    with pytest.raises(ValueError, match="both be labelled '1'"):
        from_contents({1: [1], "1": [2]})


def test_two_nans_raise_label_clash():
    with pytest.raises(ValueError, match="labelled 'nan'"):
        from_contents({float("nan"): [1], float("nan"): [2]})


def test_equal_values_are_one_category():
    # 1, 1.0 and True compare equal, so they are one category, as dict keys are
    data = from_memberships([[1], [1.0], [True]])
    assert data.categories == [1]
    with pytest.raises(ValueError, match=r"duplicate category 1\.0 \(equal to 1\)"):
        UpSetData([1, 1.0], np.zeros((1, 2), dtype=bool))


def test_unhashable_category_raises():
    with pytest.raises(TypeError, match="hashable"):
        UpSetData([["a"]], np.zeros((1, 1), dtype=bool))


# ------------------------------------------------------------------- guards


def many_categories(n):
    return from_contents({f"c{i}": {i} for i in range(n)})


def test_include_empty_subsets_guard():
    with pytest.raises(ValueError, match="1,048,576 intersections"):
        many_categories(20).subsets(include_empty_subsets=True)


def test_include_empty_subsets_degree_bounds_keep_it_small():
    # 30 categories: 2**30 overall, but only 1 + 30 + 435 up to degree 2
    subs = many_categories(30).subsets(include_empty_subsets=True, max_degree=2)
    assert len(subs) == 1 + 30 + 435
    subs = many_categories(30).subsets(
        include_empty_subsets=True, min_degree=29, max_degree=30
    )
    assert len(subs) == 30 + 1


def test_include_empty_subsets_matches_degree_filter():
    data = from_contents({"a": {1}, "b": {2}, "c": {1, 2}})
    subs = data.subsets(include_empty_subsets=True, min_degree=1, max_degree=2)
    assert {s.degree for s in subs} == {1, 2}
    assert len(subs) == 3 + 3
