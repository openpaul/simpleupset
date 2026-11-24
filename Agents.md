# Agent instructions

## Goal

A small UpSet plot package with a simple interface. The main input is a
plain dict of sets or lists. Users of the legacy
[UpSetPlot](https://github.com/jnothman/UpSetPlot) package should be able to
switch quickly: accept its input formats and argument names. Full API
compatibility beyond that is not a goal.

## Stack

- uv as package manager (`uv sync`, `uv add`, `uv run`).
- Runtime dependencies: numpy and matplotlib only. Prefer numpy or plain
  Python. If a dataframe library is ever needed internally, use polars, not
  pandas.
- Drawing with matplotlib.
- Tests with pytest.
- CI with GitHub Actions.
- Docs with Sphinx and the Furo theme, deployed to GitHub Pages.

## API

- `upsetplot(data, fig=None, **kwargs)` is the main entry point. `plot` is an
  alias for drop-in use (`from upsetplot import plot` becomes
  `from simpleupset import plot`). Keep both.
- `UpSet(data, ...).plot(fig)` keeps the legacy argument names and returns the
  legacy axes dict (`matrix`, `intersections`, `totals`, `shading`).
- Accepted inputs: dict of `{category: iterable}`, `UpSetData`, and the legacy
  pandas Series/DataFrame with a boolean MultiIndex. pandas is detected by
  duck typing and is never imported by the library; it is a dev/docs
  dependency only.
- Bars show exclusive intersections (elements in exactly that combination).
- Category names can be any hashable and are kept as given; `str(name)` is
  only used for labels. Equal values (`1`, `1.0`, `True`) are one category,
  as with dict keys. Names that would share a label (`1` and `"1"`) raise.
- Intentional differences from the legacy package: the `from_*` helpers
  return `UpSetData`, not pandas objects. Not planned: `generate_*` sample
  data helpers, `query` (use `UpSet(...).subsets` / `.totals`), `add_catplot`.
- Stacked bars: `stack_by` (dict element->group, function, per-row list, or
  DataFrame column) and `stack_colors`. Both bar charts are stacked; the
  legend lives in its own axes in the empty grid corner.
- Maybe later: `style_subsets`.

## Layout

- `src/simpleupset/data.py`: input normalisation and intersection
  aggregation.
- `src/simpleupset/plotting.py`: `UpSet` and `upsetplot`/`plot`.
- `tests/`: pytest. `tests/test_docs_examples.py` checks the hand-written
  expected tables in `docs/examples.rst`; update both together.
- `docs/`: Sphinx sources. Examples use matplotlib's `plot` directive.

## Commands

```bash
uv run pytest
rm -rf docs/_build && uv run --group docs sphinx-build -W docs docs/_build/html
```

The plot directive caches images, so do a clean rebuild after changing
plotting code. Look at the rendered PNGs when changing how plots look.

Image regression tests (`tests/test_images.py`) compare renders to
`tests/baseline/*.png`. After an intended visual change, run
`uv run pytest tests/test_images.py --regen-images`, look at every changed
baseline before committing, and commit them with the code change. Failures
write the render and a diff to `tests/image_results/` (CI uploads them as an
artifact). Baselines are tied to the matplotlib minor version in
`tests/baseline/matplotlib-version.txt` (text rendering differs between
versions); on other versions the tests skip, except in the CI job with
`REQUIRE_IMAGE_TESTS=1` (Python 3.12), where a mismatch fails. Regenerate
under Python 3.12 when the locked matplotlib changes.

## Commits

- Atomic commits, authored as `claude <claude@paulsaary.de>`.
- The agent environment may have no ssh; if `git push` fails, ask the user
  to push.

## Releases

Release after user-facing changes (features, fixes, API changes):

1. `uv version --bump patch` (use `minor` for breaking API changes while
   below 1.0.0).
2. Update the tag in the install examples (`README.md`, `docs/install.rst`).
3. Commit as "Release vX.Y.Z", then `git tag -a vX.Y.Z -m "vX.Y.Z"` on that
   commit.

The tag must match the version in `pyproject.toml`. Never move or delete
existing tags.
