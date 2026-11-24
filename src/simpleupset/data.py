"""Input normalisation and intersection aggregation.

Everything is reduced to an :class:`UpSetData`: a boolean membership matrix
(one row per element, one column per category) plus one weight per row.
Only numpy is required; pandas objects produced by the legacy ``upsetplot``
package are accepted through duck typing, without importing pandas.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "UpSetData",
    "Subset",
    "from_contents",
    "from_memberships",
    "from_indicators",
    "to_upset_data",
    "resolve_groups",
    "StackedSizes",
    "stacked_sizes",
]

#: Most intersections ``include_empty_subsets=True`` may generate (2**16).
MAX_EMPTY_SUBSETS = 65_536

_SORT_BY = ("cardinality", "-cardinality", "degree", "-degree", "input", "-input")
_SORT_CATEGORIES_BY = ("cardinality", "-cardinality", "input", "-input", None)


@dataclass(frozen=True)
class Subset:
    """One exclusive intersection: elements in exactly ``categories``."""

    categories: frozenset[Hashable]
    membership: tuple[bool, ...]
    size: float
    count: int

    @property
    def degree(self) -> int:
        return len(self.categories)


@dataclass
class UpSetData:
    """Normalised UpSet input.

    Attributes
    ----------
    categories:
        Category names, in input order. Any hashable value works (str, int,
        float, tuple, ...); names are kept as given. Values that compare
        equal, such as ``1``, ``1.0`` and ``True``, are the same category, as
        in a dict. Two categories must not share a label (``str(name)``),
        so ``1`` and ``"1"`` together raise ``ValueError``.
    membership:
        ``(n_rows, n_categories)`` boolean array.
    weights:
        ``(n_rows,)`` float array; the value summed per subset. All ones when
        subsets should be sized by element count.
    elements:
        One identity per row: the element itself for :func:`from_contents`,
        otherwise the row position. Used to look up ``stack_by`` groups.
    """

    categories: list[Hashable]
    membership: np.ndarray
    weights: np.ndarray = field(default=None)  # type: ignore[assignment]
    elements: list[Any] = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.categories = list(self.categories)
        for c in self.categories:
            try:
                hash(c)
            except TypeError:
                raise TypeError(
                    f"category names must be hashable, got {type(c).__name__}: {c!r}"
                ) from None
        m = np.asarray(self.membership, dtype=bool)
        if m.ndim != 2 or m.shape[1] != len(self.categories):
            raise ValueError(
                f"membership must have shape (n, {len(self.categories)}), got {m.shape}"
            )
        seen: dict[Hashable, Hashable] = {}
        for c in self.categories:
            if c in seen:
                also = "" if repr(seen[c]) == repr(c) else f" (equal to {seen[c]!r})"
                raise ValueError(f"duplicate category {c!r}{also}")
            seen[c] = c
        by_label: dict[str, Hashable] = {}
        for c in self.categories:
            other = by_label.setdefault(str(c), c)
            if other is not c:
                raise ValueError(
                    f"categories {other!r} and {c!r} would both be labelled "
                    f"{str(c)!r}; rename one"
                )
        self.membership = m
        if self.weights is None:
            self.weights = np.ones(m.shape[0], dtype=float)
        else:
            w = np.asarray(self.weights, dtype=float)
            if w.shape != (m.shape[0],):
                raise ValueError(f"weights must have shape ({m.shape[0]},), got {w.shape}")
            self.weights = w
        if self.elements is None:
            self.elements = list(range(m.shape[0]))
        else:
            self.elements = list(self.elements)
            if len(self.elements) != m.shape[0]:
                raise ValueError(
                    f"elements must have length {m.shape[0]}, got {len(self.elements)}"
                )

    @property
    def n_categories(self) -> int:
        return len(self.categories)

    @property
    def labels(self) -> list[str]:
        """Category labels as drawn on the plot: ``str(name)``."""
        return [str(c) for c in self.categories]

    def category_totals(self) -> dict[Hashable, float]:
        """Summed weight of every row belonging to each category."""
        totals = self.weights @ self.membership
        return dict(zip(self.categories, totals.tolist()))

    def subsets(
        self,
        *,
        sort_by: str | None = "degree",
        include_empty_subsets: bool = False,
        min_subset_size: float | None = None,
        max_subset_size: float | None = None,
        min_degree: int | None = None,
        max_degree: int | None = None,
    ) -> list[Subset]:
        """Aggregate rows into exclusive intersections, filtered and sorted."""
        if sort_by not in _SORT_BY and sort_by is not None:
            raise ValueError(f"sort_by must be one of {_SORT_BY}, got {sort_by!r}")
        m = self.membership
        if m.shape[0]:
            keys, first, inverse = np.unique(m, axis=0, return_index=True, return_inverse=True)
            inverse = inverse.reshape(-1)
            sizes = np.bincount(inverse, weights=self.weights, minlength=len(keys))
            counts = np.bincount(inverse, minlength=len(keys))
            # restore first-appearance ("input") order
            order = np.argsort(first, kind="stable")
            found = [(tuple(map(bool, keys[i])), float(sizes[i]), int(counts[i])) for i in order]
        else:
            found = []

        if include_empty_subsets:
            n = self.n_categories
            lo = 0 if min_degree is None else max(min_degree, 0)
            hi = n if max_degree is None else min(max_degree, n)
            n_candidates = sum(math.comb(n, k) for k in range(lo, hi + 1))
            if n_candidates > MAX_EMPTY_SUBSETS:
                raise ValueError(
                    f"include_empty_subsets=True with {n} categories means "
                    f"{n_candidates:,} intersections (limit {MAX_EMPTY_SUBSETS:,}); "
                    "narrow it with min_degree/max_degree or drop the option"
                )
            seen = {k for k, _, _ in found}
            for k in range(lo, hi + 1):
                for members in itertools.combinations(range(n), k):
                    key = tuple(j in members for j in range(n))
                    if key not in seen:
                        found.append((key, 0.0, 0))

        result = [
            Subset(
                frozenset(c for c, flag in zip(self.categories, key) if flag),
                key,
                size,
                count,
            )
            for key, size, count in found
        ]

        def keep(s: Subset) -> bool:
            return not (
                (min_subset_size is not None and s.size < min_subset_size)
                or (max_subset_size is not None and s.size > max_subset_size)
                or (min_degree is not None and s.degree < min_degree)
                or (max_degree is not None and s.degree > max_degree)
            )

        result = [s for s in result if keep(s)]
        return _sort_subsets(result, sort_by)

    def sort_categories(self, sort_categories_by: str | None = "cardinality") -> UpSetData:
        """Return a copy with categories reordered."""
        if sort_categories_by not in _SORT_CATEGORIES_BY:
            raise ValueError(
                f"sort_categories_by must be one of {_SORT_CATEGORIES_BY}, "
                f"got {sort_categories_by!r}"
            )
        idx = list(range(self.n_categories))
        if sort_categories_by in ("cardinality", "-cardinality"):
            totals = self.weights @ self.membership
            sign = -1 if sort_categories_by == "cardinality" else 1
            idx.sort(key=lambda i: sign * totals[i])  # stable: ties keep input order
        elif sort_categories_by == "-input":
            idx.reverse()
        return UpSetData(
            [self.categories[i] for i in idx],
            self.membership[:, idx],
            self.weights.copy(),
            self.elements,
        )


def _sort_subsets(subsets: list[Subset], sort_by: str | None) -> list[Subset]:
    if sort_by in (None, "input"):
        return list(subsets)
    if sort_by == "-input":
        return subsets[::-1]
    if sort_by == "cardinality":
        return sorted(subsets, key=lambda s: -s.size)
    if sort_by == "-cardinality":
        return sorted(subsets, key=lambda s: s.size)
    # degree: by degree, then by position of categories (leftmost first), as upsetplot
    def degree_key(s: Subset) -> tuple:
        return (s.degree, tuple(not f for f in s.membership))

    return sorted(subsets, key=degree_key, reverse=(sort_by == "-degree"))


# --------------------------------------------------------------------------- #
# constructors (names mirror the legacy upsetplot API)
# --------------------------------------------------------------------------- #


def from_contents(contents: Mapping[Any, Iterable[Any]]) -> UpSetData:
    """Build from ``{category: elements}``, e.g. a dict of sets.

    Each distinct element is one row; elements are matched by equality, so
    they must be hashable.
    """
    categories = list(contents)
    index: dict[Any, int] = {}
    rows: list[list[bool]] = []
    for j, cat in enumerate(categories):
        elements = contents[cat]
        if isinstance(elements, (str, bytes)):
            raise TypeError(
                f"contents of category {cat!r} is a string; pass a set/list of elements"
            )
        for el in elements:
            i = index.get(el)
            if i is None:
                i = index[el] = len(rows)
                rows.append([False] * len(categories))
            rows[i][j] = True
    membership = np.array(rows, dtype=bool).reshape(len(rows), len(categories))
    return UpSetData(categories, membership, elements=list(index))


def from_memberships(
    memberships: Iterable[Iterable[Any]], data: Sequence[float] | None = None
) -> UpSetData:
    """Build from one category list per element, e.g. ``[["a"], ["a", "b"], []]``.

    ``data`` optionally gives a weight per element (summed instead of counted).
    """
    memberships = [list(m) if not isinstance(m, str) else [m] for m in memberships]
    categories: list[Any] = []
    pos: dict[Any, int] = {}
    for m in memberships:
        for c in m:
            if c not in pos:
                pos[c] = len(categories)
                categories.append(c)
    membership = np.zeros((len(memberships), len(categories)), dtype=bool)
    for i, m in enumerate(memberships):
        for c in m:
            membership[i, pos[c]] = True
    weights = None if data is None else np.asarray(data, dtype=float)
    return UpSetData(categories, membership, weights)


def from_indicators(
    indicators: Mapping[Any, Sequence[bool]] | Any,
    data: Sequence[float] | None = None,
) -> UpSetData:
    """Build from boolean indicator columns.

    Accepts ``{category: bool_sequence}`` or any DataFrame-like object with
    ``.columns`` whose columns are boolean.
    """
    if hasattr(indicators, "columns") and not isinstance(indicators, Mapping):
        categories = list(indicators.columns)
        columns = [np.asarray(indicators[c]) for c in categories]
    else:
        categories = list(indicators)
        columns = [np.asarray(indicators[c]) for c in categories]
    if columns:
        membership = np.column_stack([c.astype(bool) for c in columns])
    else:
        membership = np.zeros((0, 0), dtype=bool)
    weights = None if data is None else np.asarray(data, dtype=float)
    return UpSetData(categories, membership, weights)


def _from_pandas(obj: Any, sum_over: str | None, subset_size: str) -> UpSetData:
    """Legacy upsetplot input: Series/DataFrame indexed by boolean levels."""
    names = list(obj.index.names)
    if any(n is None for n in names):
        raise ValueError("every boolean index level must be named after its category")
    tuples = [t if isinstance(t, tuple) else (t,) for t in obj.index]
    membership = np.array(tuples, dtype=bool).reshape(len(tuples), len(names))
    is_series = not hasattr(obj, "columns")

    if subset_size == "auto":
        if is_series:
            subset_size = "count" if obj.index.has_duplicates else "sum"
        else:
            subset_size = "count" if sum_over is None else "sum"

    if subset_size == "count":
        if sum_over is not None:
            raise ValueError("sum_over cannot be used with subset_size='count'")
        weights = None
    elif subset_size == "sum":
        if is_series:
            values = obj.to_numpy() if hasattr(obj, "to_numpy") else obj.values
        else:
            if sum_over is None:
                raise ValueError("sum_over is required for a DataFrame with subset_size='sum'")
            values = obj[sum_over].to_numpy()
        weights = np.asarray(values, dtype=float)
    else:
        raise ValueError(f"subset_size must be 'auto', 'count' or 'sum', got {subset_size!r}")
    return UpSetData(names, membership, weights)


def to_upset_data(
    data: Any, *, subset_size: str = "auto", sum_over: str | None = None
) -> UpSetData:
    """Normalise any supported input into :class:`UpSetData`.

    Supported inputs:

    * :class:`UpSetData`
    * ``dict`` of ``{category: iterable of elements}`` (e.g. a dict of sets)
    * pandas ``Series``/``DataFrame`` with a boolean (Multi)Index, as produced
      by the legacy ``upsetplot.from_contents``/``from_memberships``.
    """
    if isinstance(data, UpSetData):
        if subset_size == "count":
            return UpSetData(data.categories, data.membership, elements=data.elements)
        return data
    if isinstance(data, Mapping):
        if sum_over is not None:
            raise ValueError("sum_over is not supported for a dict of sets")
        return from_contents(data)
    if hasattr(data, "index") and hasattr(data.index, "names"):
        return _from_pandas(data, sum_over, subset_size)
    raise TypeError(
        "data must be a dict of sets, UpSetData, or a pandas Series/DataFrame with "
        f"a boolean index; got {type(data).__name__}"
    )


# --------------------------------------------------------------------------- #
# stacking
# --------------------------------------------------------------------------- #


def resolve_groups(data: UpSetData, stack_by: Any, source: Any = None) -> list[Hashable]:
    """One group per row of ``data``.

    ``stack_by`` is a mapping ``{element: group}``, a callable
    ``element -> group``, a sequence with one group per row, or (only when
    ``source`` is a DataFrame) the name of one of its columns.
    """
    n = data.membership.shape[0]
    if isinstance(stack_by, str):
        if source is not None and hasattr(source, "columns") and stack_by in source.columns:
            groups = list(source[stack_by])
        else:
            raise TypeError(
                f"stack_by={stack_by!r} is a column name, which needs a DataFrame "
                "with that column; pass a dict {element: group}, a function, or a "
                "list with one group per element instead"
            )
    elif isinstance(stack_by, Mapping):
        missing = [e for e in data.elements if e not in stack_by]
        if missing:
            shown = ", ".join(map(repr, missing[:5])) + (", ..." if len(missing) > 5 else "")
            raise ValueError(f"stack_by has no group for {len(missing)} element(s): {shown}")
        groups = [stack_by[e] for e in data.elements]
    elif callable(stack_by):
        groups = [stack_by(e) for e in data.elements]
    else:
        groups = list(stack_by)
        if len(groups) != n:
            raise ValueError(f"stack_by must have one group per row ({n}), got {len(groups)}")
    for g in groups:
        try:
            hash(g)
        except TypeError:
            raise TypeError(f"stack_by groups must be hashable, got {g!r}") from None
    return groups


@dataclass
class StackedSizes:
    """Subset and category sizes split by group.

    ``subsets[i, k]`` is the size of subset ``i`` within group ``groups[k]``;
    ``totals[j, k]`` the same for category ``j``.
    """

    groups: list[Hashable]
    subsets: np.ndarray
    totals: np.ndarray


def stacked_sizes(
    data: UpSetData,
    subsets: Sequence[Subset],
    row_groups: Sequence[Hashable],
    order: Sequence[Hashable] | None = None,
) -> StackedSizes:
    """Break the sizes of ``subsets`` and of each category down by group.

    Groups are ordered by ``order`` if given (it must contain every group),
    otherwise sorted, or in order of first appearance if they cannot be
    sorted.
    """
    present = list(dict.fromkeys(row_groups))
    if order is not None:
        order = list(order)
        missing = [g for g in present if g not in order]
        if missing:
            raise ValueError(f"no colour/order given for group(s): {missing!r}")
        groups = [g for g in order if g in set(present)] if present else order
    else:
        try:
            groups = sorted(present)
        except TypeError:
            groups = present
    code = {g: k for k, g in enumerate(groups)}
    codes = np.array([code[g] for g in row_groups], dtype=int).reshape(-1)

    n_rows, n_groups = data.membership.shape[0], len(groups)
    per_group = np.zeros((n_rows, n_groups))
    if n_rows:
        per_group[np.arange(n_rows), codes] = data.weights

    totals = data.membership.T.astype(float) @ per_group
    row_of = {}
    for i, row in enumerate(map(tuple, data.membership.tolist())):
        row_of.setdefault(row, []).append(i)
    sub = np.zeros((len(subsets), n_groups))
    for i, s in enumerate(subsets):
        rows = row_of.get(tuple(s.membership))
        if rows:
            sub[i] = per_group[rows].sum(axis=0)
    return StackedSizes(groups, sub, totals)
