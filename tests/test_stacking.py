import numpy as np
import pytest
from matplotlib.colors import to_rgba

from simpleupset import UpSet, from_contents, from_memberships, upsetplot
from simpleupset.data import resolve_groups, stacked_sizes

ITEMS = {"a": [1, 2, 3, 4, 6, 7], "b": [2, 3, 5, 6, 19, 21], "c": [4, 5, 21, 30, 31]}


def parity(e):
    return "case" if e % 2 else "control"


def by_subset(upset):
    st = upset.stacked
    return {
        "".join(sorted(s.categories)): dict(zip(st.groups, st.subsets[i].tolist()))
        for i, s in enumerate(upset.subsets)
    }


# ------------------------------------------------------------------ groups


def test_mapping_callable_and_sequence_agree():
    data = from_contents(ITEMS)
    mapping = {e: parity(e) for e in data.elements}
    seq = [parity(e) for e in data.elements]
    assert resolve_groups(data, mapping) == resolve_groups(data, parity) == seq
    assert resolve_groups(data, seq) == seq


def test_missing_elements_in_mapping():
    with pytest.raises(ValueError, match=r"no group for 2 element\(s\): 30, 31"):
        UpSet(ITEMS, stack_by={e: "x" for e in [1, 2, 3, 4, 5, 6, 7, 19, 21]})


def test_wrong_length_sequence():
    with pytest.raises(ValueError, match="one group per row"):
        UpSet(ITEMS, stack_by=["x", "y"])


def test_column_name_needs_dataframe():
    with pytest.raises(TypeError, match="column name"):
        UpSet(ITEMS, stack_by="sex")


def test_unhashable_group():
    with pytest.raises(TypeError, match="hashable"):
        UpSet(ITEMS, stack_by=lambda e: [e])


# ------------------------------------------------------------------- sizes


def test_stacked_sizes_by_hand():
    upset = UpSet(ITEMS, stack_by=parity)
    assert upset.stacked.groups == ["case", "control"]
    assert by_subset(upset) == {
        "a": {"case": 2, "control": 0},  # 1, 7
        "b": {"case": 1, "control": 0},  # 19
        "c": {"case": 1, "control": 1},  # 31 | 30
        "ab": {"case": 1, "control": 2},  # 3 | 2, 6
        "ac": {"case": 0, "control": 1},  # 4
        "bc": {"case": 2, "control": 0},  # 5, 21
    }
    totals = dict(zip(upset.data.categories, upset.stacked.totals.tolist()))
    assert totals == {"a": [3, 3], "b": [4, 2], "c": [3, 2]}


def test_stacks_add_up_to_unstacked_sizes():
    upset = UpSet(ITEMS, stack_by=lambda e: e % 3)
    assert upset.stacked.subsets.sum(axis=1).tolist() == [s.size for s in upset.subsets]
    assert upset.stacked.totals.sum(axis=1).tolist() == [
        upset.totals[c] for c in upset.data.categories
    ]


def test_weighted_rows_stack_by_list():
    data = from_memberships([["x"], ["x"], ["x", "y"]], data=[1.5, 2.0, 4.0])
    upset = UpSet(data, stack_by=["p", "q", "q"], sort_by="input")
    assert upset.stacked.subsets.tolist() == [[1.5, 2.0], [0.0, 4.0]]


def test_group_order_sorted_then_first_appearance():
    data = from_contents({"a": [1, 2, 3]})
    groups = ["z", "a", "m"]
    assert stacked_sizes(data, data.subsets(), groups).groups == ["a", "m", "z"]
    mixed = ["z", 1, "z"]  # not sortable: keep first appearance
    assert stacked_sizes(data, data.subsets(), mixed).groups == ["z", 1]


def test_colour_mapping_sets_order_and_must_cover_groups():
    upset = UpSet(ITEMS, stack_by=parity, stack_colors={"control": "red", "case": "blue"})
    assert upset.stacked.groups == ["control", "case"]
    with pytest.raises(ValueError, match="case"):
        UpSet(ITEMS, stack_by=parity, stack_colors={"control": "red"})


def test_empty_subsets_get_zero_stacks():
    upset = UpSet({"a": [1], "b": [2]}, stack_by=parity, include_empty_subsets=True)
    sizes = by_subset(upset)
    assert sizes["ab"] == {"case": 0, "control": 0}
    assert sizes[""] == {"case": 0, "control": 0}


def test_legacy_dataframe_column():
    pd = pytest.importorskip("pandas")
    index = pd.MultiIndex.from_tuples(
        [(True, False), (True, False), (True, True)], names=["a", "b"]
    )
    df = pd.DataFrame({"sex": ["f", "m", "f"]}, index=index)
    upset = UpSet(df, stack_by="sex", sort_by="input")
    assert upset.stacked.subsets.tolist() == [[1, 1], [1, 0]]


# ---------------------------------------------------------------- plotting


def segment_heights(ax, horizontal=True):
    return [
        [p.get_height() if horizontal else p.get_width() for p in c]
        for c in ax.containers
    ]


def test_bars_are_stacked_with_legend():
    axes = upsetplot(ITEMS, stack_by=parity, sort_by="input")
    inter = axes["intersections"]
    case, control = segment_heights(inter)
    assert [a + b for a, b in zip(case, control)] == [2, 3, 1, 2, 1, 2]  # a, ab, ac, bc, b, c (first appearance)
    # second segment starts where the first ends
    assert [p.get_y() for p in inter.containers[1]] == case
    assert [t.get_text() for t in inter.get_legend().get_texts()] == ["case", "control"]
    assert len(axes["totals"].containers) == 2


def test_count_labels_show_stack_totals():
    axes = upsetplot(ITEMS, stack_by=parity, sort_by="input", show_counts=True)
    labels = [t.get_text() for t in axes["intersections"].texts]
    assert labels == ["2", "3", "1", "2", "1", "2"]


def test_colours_applied():
    axes = upsetplot(ITEMS, stack_by=parity, stack_colors=["red", "blue"])
    first, second = axes["intersections"].containers
    assert first[0].get_facecolor() == to_rgba("red")
    assert second[0].get_facecolor() == to_rgba("blue")


def test_colormap_name():
    axes = upsetplot(ITEMS, stack_by=lambda e: e % 3, stack_colors="viridis")
    colors = [c[0].get_facecolor() for c in axes["intersections"].containers]
    assert len(set(colors)) == 3


def test_vertical_stacking():
    axes = upsetplot(ITEMS, stack_by=parity, orientation="vertical", sort_by="input")
    case, control = segment_heights(axes["intersections"], horizontal=False)
    assert [a + b for a, b in zip(case, control)] == [2, 3, 1, 2, 1, 2]  # a, ab, ac, bc, b, c (first appearance)


def test_legend_title_from_column_name():
    pd = pytest.importorskip("pandas")
    index = pd.MultiIndex.from_tuples([(True,), (True,)], names=["a"])
    df = pd.DataFrame({"sex": ["f", "m"]}, index=index)
    axes = upsetplot(df, stack_by="sex")
    assert axes["intersections"].get_legend().get_title().get_text() == "sex"


def test_no_legend_without_stacking():
    axes = upsetplot(ITEMS)
    assert axes["intersections"].get_legend() is None
    assert np.isclose(sum(p.get_height() for p in axes["intersections"].patches), 11)
