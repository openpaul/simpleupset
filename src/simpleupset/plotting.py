"""Matplotlib rendering, API-compatible with the legacy ``upsetplot.UpSet``."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from simpleupset.data import Subset, UpSetData, to_upset_data

__all__ = ["UpSet", "plot", "upsetplot"]


class UpSet:
    """UpSet plot of set intersections.

    Parameters mirror ``upsetplot.UpSet`` so existing code keeps working.

    Parameters
    ----------
    data:
        A dict of ``{category: set_of_elements}``, an :class:`UpSetData`, or a
        legacy pandas Series/DataFrame with a boolean MultiIndex.
    orientation:
        ``"horizontal"`` (intersections as columns) or ``"vertical"``.
    sort_by:
        Subset order: ``"cardinality"``, ``"degree"``, ``"input"``, each
        optionally prefixed with ``"-"`` to reverse, or ``None`` (= input).
    sort_categories_by:
        Category order: ``"cardinality"``, ``"input"`` (optionally ``"-"``
        prefixed) or ``None``.
    subset_size:
        ``"auto"``, ``"count"`` or ``"sum"`` (legacy semantics).
    sum_over:
        Column to sum over when ``data`` is a DataFrame.
    min_subset_size, max_subset_size, min_degree, max_degree:
        Hide subsets outside these bounds.
    facecolor:
        Colour of bars and filled dots. ``"auto"`` means black.
    other_dots_color, shading_color:
        Colour for empty matrix dots / alternating row shading. A float is an
        alpha applied to ``facecolor``.
    with_lines:
        Draw lines connecting the dots of each intersection.
    element_size:
        Side of one matrix cell in points; sets the figure size. ``None``
        keeps the figure size as given.
    intersection_plot_elements, totals_plot_elements:
        Size of the bar charts, in matrix cells.
    show_counts, show_percentages:
        Annotate bars. ``True`` or a format string (``"{:,}"`` or ``"%d"``).
    include_empty_subsets:
        Show all ``2**n`` intersections, even empty ones.
    """

    def __init__(
        self,
        data: Any,
        orientation: str = "horizontal",
        sort_by: str | None = "degree",
        sort_categories_by: str | None = "cardinality",
        subset_size: str = "auto",
        sum_over: str | None = None,
        min_subset_size: float | None = None,
        max_subset_size: float | None = None,
        min_degree: int | None = None,
        max_degree: int | None = None,
        facecolor: Any = "auto",
        other_dots_color: Any = 0.18,
        shading_color: Any = 0.05,
        with_lines: bool = True,
        element_size: float | None = 32,
        intersection_plot_elements: int = 6,
        totals_plot_elements: int = 2,
        show_counts: bool | str = "",
        show_percentages: bool | str = False,
        include_empty_subsets: bool = False,
    ) -> None:
        if orientation not in ("horizontal", "vertical"):
            raise ValueError(f"orientation must be 'horizontal' or 'vertical', got {orientation!r}")
        upset_data = to_upset_data(data, subset_size=subset_size, sum_over=sum_over)
        if sort_categories_by is not None:
            upset_data = upset_data.sort_categories(sort_categories_by)
        self.data: UpSetData = upset_data
        self.subsets: list[Subset] = upset_data.subsets(
            sort_by=sort_by,
            include_empty_subsets=include_empty_subsets,
            min_subset_size=min_subset_size,
            max_subset_size=max_subset_size,
            min_degree=min_degree,
            max_degree=max_degree,
        )
        self.totals: dict[str, float] = upset_data.category_totals()
        self._grand_total = float(upset_data.weights.sum())

        self._horizontal = orientation == "horizontal"
        self._facecolor = "black" if facecolor == "auto" else facecolor
        self._other_dots_color = _resolve_color(other_dots_color, self._facecolor)
        self._shading_color = _resolve_color(shading_color, self._facecolor)
        self._with_lines = with_lines
        self._element_size = element_size
        self._inter_elems = intersection_plot_elements
        self._totals_elems = totals_plot_elements
        self._show_counts = show_counts
        self._show_percentages = show_percentages

    # ------------------------------------------------------------------ public

    def plot(self, fig: Figure | None = None) -> dict[str, Any]:
        """Draw the plot. Returns axes keyed ``matrix``, ``intersections``,
        ``totals`` and ``shading`` (as in upsetplot)."""
        if fig is None:
            fig = plt.figure()
        axes = self._make_axes(fig)
        self._plot_matrix(axes["matrix"])
        self._plot_intersections(axes["intersections"])
        self._plot_totals(axes["totals"])
        return axes

    # ----------------------------------------------------------------- layout

    def _label_elements(self) -> float:
        """Room for category labels, in matrix cells."""
        longest = max((len(c) for c in self.data.categories), default=0)
        fontsize = plt.rcParams["ytick.labelsize"]
        if isinstance(fontsize, str):
            fontsize = plt.rcParams["font.size"]
        cell = self._element_size or 32
        return longest * 0.6 * fontsize / cell + 0.5

    def _make_axes(self, fig: Figure) -> dict[str, Any]:
        n_sub = max(len(self.subsets), 1)
        n_cat = max(self.data.n_categories, 1)
        labels = self._label_elements()
        # long axis: [totals, labels, matrix]; short axis: [intersections, matrix]
        long_ratios = [self._totals_elems, labels, n_sub]
        short_ratios = [self._inter_elems, n_cat]

        if self._element_size is not None:
            size_in = self._element_size / 72
            w, h = sum(long_ratios) * size_in, sum(short_ratios) * size_in
            fig.set_size_inches(*((w, h) if self._horizontal else (h, w)))

        if self._horizontal:
            gs = fig.add_gridspec(
                2, 3, width_ratios=long_ratios, height_ratios=short_ratios,
                wspace=0, hspace=0,
            )
            matrix = fig.add_subplot(gs[1, 2])
            inter = fig.add_subplot(gs[0, 2], sharex=matrix)
            totals = fig.add_subplot(gs[1, 0], sharey=matrix)
        else:
            # transpose: [totals; labels; matrix] rows, [matrix | intersections] cols
            gs = fig.add_gridspec(
                3, 2, height_ratios=long_ratios, width_ratios=short_ratios[::-1],
                wspace=0, hspace=0,
            )
            matrix = fig.add_subplot(gs[2, 0])
            inter = fig.add_subplot(gs[2, 1], sharey=matrix)
            totals = fig.add_subplot(gs[0, 0], sharex=matrix)
        return {"matrix": matrix, "intersections": inter, "totals": totals, "shading": matrix}

    def _xy(self, sub_pos: np.ndarray, cat_pos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return (sub_pos, cat_pos) if self._horizontal else (cat_pos, sub_pos)

    # ------------------------------------------------------------------ parts

    def _plot_matrix(self, ax: Any) -> None:
        n_sub, n_cat = len(self.subsets), self.data.n_categories
        for j in range(0, n_cat, 2):
            span = ax.axhspan if self._horizontal else ax.axvspan
            span(j - 0.5, j + 0.5, color=self._shading_color, zorder=0, lw=0)

        grid = np.array([s.membership for s in self.subsets], dtype=bool).reshape(n_sub, n_cat)
        sub_idx, cat_idx = np.meshgrid(np.arange(n_sub), np.arange(n_cat), indexing="ij")
        dot_size = (0.5 * (self._element_size or 32)) ** 2

        x, y = self._xy(sub_idx[~grid], cat_idx[~grid])
        ax.scatter(x, y, s=dot_size, c=[self._other_dots_color], zorder=2, lw=0)
        x, y = self._xy(sub_idx[grid], cat_idx[grid])
        ax.scatter(x, y, s=dot_size, c=[to_rgba(self._facecolor)], zorder=3, lw=0)

        if self._with_lines:
            for i, row in enumerate(grid):
                members = np.flatnonzero(row)
                if len(members) > 1:
                    x, y = self._xy(np.array([i, i]), members[[0, -1]])
                    ax.plot(x, y, color=self._facecolor, lw=2, zorder=2.5,
                            solid_capstyle="round")

        sub_lim, cat_lim = (-0.5, max(n_sub, 1) - 0.5), (max(n_cat, 1) - 0.5, -0.5)
        if self._horizontal:
            ax.set_xlim(*sub_lim)
            ax.set_ylim(*cat_lim)
            ax.set_yticks(range(n_cat), self.data.categories)
            ax.set_xticks([])
        else:
            ax.set_xlim(*cat_lim[::-1])
            ax.set_ylim(*sub_lim[::-1])
            ax.set_xticks(range(n_cat), self.data.categories, rotation=90)
            ax.xaxis.tick_top()
            ax.set_yticks([])
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

    def _plot_intersections(self, ax: Any) -> None:
        sizes = [s.size for s in self.subsets]
        pos = np.arange(len(sizes))
        if self._horizontal:
            bars = ax.bar(pos, sizes, width=0.5, color=self._facecolor, zorder=10)
            ax.set_ylabel("Intersection size")
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
            _hide_spines(ax, "top", "right", "bottom")
            ax.yaxis.grid(True, lw=0.5, color="#dddddd")
        else:
            bars = ax.barh(pos, sizes, height=0.5, color=self._facecolor, zorder=10)
            ax.set_xlabel("Intersection size")
            ax.tick_params(axis="y", left=False, labelleft=False)
            _hide_spines(ax, "top", "right", "left")
            ax.xaxis.grid(True, lw=0.5, color="#dddddd")
        ax.set_axisbelow(True)
        self._label_bars(ax, bars, sizes, along_x=not self._horizontal)

    def _plot_totals(self, ax: Any) -> None:
        sizes = [self.totals[c] for c in self.data.categories]
        pos = np.arange(len(sizes))
        if self._horizontal:
            bars = ax.barh(pos, sizes, height=0.5, color=self._facecolor, zorder=10)
            ax.invert_xaxis()  # bars grow leftwards, away from the matrix
            ax.tick_params(axis="y", left=False, labelleft=False)
            _hide_spines(ax, "top", "left", "right")
            ax.xaxis.grid(True, lw=0.5, color="#dddddd")
        else:
            bars = ax.bar(pos, sizes, width=0.5, color=self._facecolor, zorder=10)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
            _hide_spines(ax, "top", "right", "bottom")
            ax.yaxis.grid(True, lw=0.5, color="#dddddd")
        ax.set_axisbelow(True)
        self._label_bars(ax, bars, sizes, along_x=self._horizontal)

    def _label_bars(self, ax: Any, bars: Any, sizes: list[float], along_x: bool) -> None:
        if all(float(v).is_integer() for v in sizes):
            (ax.xaxis if along_x else ax.yaxis).set_major_locator(MaxNLocator(nbins="auto", integer=True))
        if not (self._show_counts or self._show_percentages):
            return
        labels = [self._format_label(v) for v in sizes]
        both = self._show_counts and self._show_percentages
        ax.bar_label(bars, labels, padding=2, fontsize="x-small" if both else "small")
        # leave room for the labels beyond the longest bar
        if sizes:
            lim = ax.get_xlim() if along_x else ax.get_ylim()
            lo, hi = sorted(lim)
            new = (lo, hi * 1.15) if lim[0] <= lim[1] else (hi * 1.15, lo)
            (ax.set_xlim if along_x else ax.set_ylim)(*new)

    def _format_label(self, value: float) -> str:
        parts = []
        if self._show_counts:
            fmt = self._show_counts
            if fmt is True:
                fmt = "{:,.0f}" if float(value).is_integer() else "{:,.2f}"
            parts.append(_apply_format(fmt, value))
        if self._show_percentages:
            fmt = "{:.1%}" if self._show_percentages is True else self._show_percentages
            frac = value / self._grand_total if self._grand_total else 0.0
            pct = _apply_format(fmt, frac)
            parts.append(f"({pct})" if parts else pct)
        return "\n".join(parts)


def upsetplot(data: Any, fig: Figure | None = None, **kwargs: Any) -> dict[str, Any]:
    """Draw an UpSet plot. ``kwargs`` are passed to :class:`UpSet`.

    >>> upsetplot({"a": [1, 2, 3], "b": [2, 3, 4], "c": [3, 5]})  # doctest: +SKIP
    """
    return UpSet(data, **kwargs).plot(fig=fig)


plot = upsetplot
"""Alias of :func:`upsetplot`, matching the legacy ``upsetplot.plot``."""


def _resolve_color(color: Any, facecolor: Any) -> tuple[float, float, float, float]:
    if isinstance(color, (int, float)) and not isinstance(color, bool):
        r, g, b, _ = to_rgba(facecolor)
        return (r, g, b, float(color))
    return to_rgba(color)


def _apply_format(fmt: str, value: float) -> str:
    if float(value).is_integer():
        value = int(value)  # so "{:,}" and "{:d}" render 3.0 as "3"
    return fmt.format(value) if "{" in fmt else fmt % value


def _hide_spines(ax: Any, *names: str) -> None:
    for name in names:
        ax.spines[name].set_visible(False)
