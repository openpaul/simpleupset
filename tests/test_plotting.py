import matplotlib.pyplot as plt
import numpy as np
import pytest

from simpleupset import UpSet, from_memberships, plot, upsetplot

CONTENTS = {"a": {1, 2, 3, 4}, "b": {3, 4, 5}, "c": {4, 6}}


def bar_heights(ax, horizontal=True):
    return [p.get_height() if horizontal else p.get_width() for p in ax.patches]


def test_plot_dict_of_sets_returns_legacy_axes():
    axes = plot(CONTENTS)
    assert set(axes) == {"matrix", "intersections", "totals", "shading"}
    # 5 non-empty exclusive intersections, default sort_by="degree"
    assert bar_heights(axes["intersections"]) == [2, 1, 1, 1, 1]
    labels = [t.get_text() for t in axes["matrix"].get_yticklabels()]
    assert labels == ["a", "b", "c"]  # sorted by cardinality
    assert [p.get_width() for p in axes["totals"].patches] == [4, 3, 2]


def test_plot_uses_given_figure():
    fig = plt.figure()
    axes = plot(CONTENTS, fig=fig)
    assert axes["matrix"].figure is fig


def test_element_size_sets_cell_size():
    fig = plt.figure()
    axes = plot(CONTENTS, fig=fig, element_size=40)
    w_pt, h_pt = fig.get_size_inches() * 72
    matrix = axes["matrix"].get_position()
    # 5 subsets x 3 categories, each cell 40pt, regardless of figure margins
    assert matrix.width * w_pt == pytest.approx(5 * 40)
    assert matrix.height * h_pt == pytest.approx(3 * 40)
    inter = axes["intersections"].get_position()
    assert inter.height * h_pt == pytest.approx(6 * 40)


LONG_LABELS = {
    "selected subset": range(0, 40),
    "connected components": range(30, 60),
    "WWWWWWWWWWWW": range(5, 12),
}


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("fontsize", [8, 10, 16])
@pytest.mark.parametrize("element_size", [32, None])
def test_long_labels_do_not_overlap_totals(orientation, fontsize, element_size):
    with plt.rc_context({"font.size": fontsize}):
        fig = plt.figure(figsize=(8, 6))
        axes = plot(LONG_LABELS, fig=fig, orientation=orientation,
                    element_size=element_size)
        renderer = fig.canvas.get_renderer()
        matrix, totals = axes["matrix"], axes["totals"]
        tick_labels = (matrix.get_yticklabels() if orientation == "horizontal"
                       else matrix.get_xticklabels())
        bars = totals.get_window_extent(renderer)
        for label in tick_labels:
            box = label.get_window_extent(renderer)
            if orientation == "horizontal":
                assert box.x0 >= bars.x1, label.get_text()
            else:
                assert box.y1 <= bars.y0, label.get_text()


def test_element_size_none_keeps_figure_size():
    fig = plt.figure(figsize=(3, 2))
    plot(CONTENTS, fig=fig, element_size=None)
    assert tuple(fig.get_size_inches()) == (3, 2)


def test_vertical_orientation():
    axes = plot(CONTENTS, orientation="vertical")
    assert bar_heights(axes["intersections"], horizontal=False) == [2, 1, 1, 1, 1]
    labels = [t.get_text() for t in axes["matrix"].get_xticklabels()]
    assert labels == ["a", "b", "c"]


def test_invalid_orientation():
    with pytest.raises(ValueError, match="orientation"):
        UpSet(CONTENTS, orientation="diagonal")


def test_matrix_dots():
    axes = plot(CONTENTS, sort_by="cardinality")
    empty, filled = axes["matrix"].collections[:2]
    # 5 subsets x 3 categories = 15 cells; memberships: a, ab, abc, b, c -> 8 filled
    assert len(filled.get_offsets()) == 8
    assert len(empty.get_offsets()) == 7
    # lines for the two multi-category intersections
    assert len(axes["matrix"].lines) == 2


def test_with_lines_false():
    axes = plot(CONTENTS, with_lines=False)
    assert len(axes["matrix"].lines) == 0


def test_show_counts_and_percentages():
    axes = plot(CONTENTS, show_counts=True, show_percentages=True, sort_by="cardinality")
    texts = [t.get_text() for t in axes["intersections"].texts]
    assert texts[0] == "2\n(33.3%)"
    totals = [t.get_text() for t in axes["totals"].texts]
    assert totals[0].startswith("4")


@pytest.mark.parametrize("fmt", ["{:,}", "%d", "{:d}"])
def test_show_counts_formats(fmt):
    axes = plot(CONTENTS, show_counts=fmt, sort_by="cardinality")
    assert axes["intersections"].texts[0].get_text() == "2"


def test_no_labels_by_default():
    axes = plot(CONTENTS)
    assert len(axes["intersections"].texts) == 0


def test_filters_reduce_bars():
    axes = plot(CONTENTS, min_degree=2)
    assert len(axes["intersections"].patches) == 2


def test_weighted_memberships():
    data = from_memberships([["x"], ["x", "y"], ["y"]], data=[1.5, 2.5, 4])
    axes = plot(data, sort_by="input")
    assert bar_heights(axes["intersections"]) == [1.5, 2.5, 4]


def test_facecolor_and_alpha_colors():
    upset = UpSet(CONTENTS, facecolor="red", other_dots_color=0.3)
    axes = upset.plot()
    assert axes["intersections"].patches[0].get_facecolor() == (1, 0, 0, 1)
    empty = axes["matrix"].collections[0]
    assert np.allclose(empty.get_facecolor()[0], (1, 0, 0, 0.3))


def test_empty_data_plots():
    axes = plot({"a": set(), "b": set()})
    assert len(axes["intersections"].patches) == 0


def test_include_empty_subsets():
    axes = plot({"a": {1}, "b": {2}}, include_empty_subsets=True)
    assert len(axes["intersections"].patches) == 4


def test_upset_exposes_subsets_and_totals():
    upset = UpSet(CONTENTS)
    assert upset.totals == {"a": 4, "b": 3, "c": 2}
    assert sum(s.size for s in upset.subsets) == 6


def test_legacy_series_input():
    pd = pytest.importorskip("pandas")
    idx = pd.MultiIndex.from_tuples(
        [(True, False), (True, True), (False, True)], names=["cat1", "cat2"]
    )
    axes = plot(pd.Series([5, 3, 2], index=idx), sort_by="cardinality")
    assert bar_heights(axes["intersections"]) == [5, 3, 2]


def test_saves_png(tmp_path):
    fig = plt.figure()
    plot(CONTENTS, fig=fig, show_counts=True)
    out = tmp_path / "upset.png"
    fig.savefig(out)
    assert out.stat().st_size > 0


def test_plot_dict_of_lists():
    items = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
    axes = plot(items, sort_by="cardinality")
    assert sorted(bar_heights(axes["intersections"]), reverse=True) == [2, 2, 1, 1, 1, 1]


def test_integer_ticks_for_counts():
    axes = plot({"a": {1, 2}, "b": {2}})
    ticks = axes["intersections"].get_yticks()
    assert all(float(t).is_integer() for t in ticks)


def test_upsetplot_is_main_name_and_plot_is_alias():
    import simpleupset

    assert simpleupset.plot is simpleupset.upsetplot
    axes = upsetplot(CONTENTS)
    assert set(axes) == {"matrix", "intersections", "totals", "shading"}


def test_int_categories_labels_and_totals():
    upset = UpSet({10: [1, 2, 3], 20: [3, 4]})
    assert upset.totals == {10: 3, 20: 2}
    axes = upset.plot()
    assert [t.get_text() for t in axes["matrix"].get_yticklabels()] == ["10", "20"]
