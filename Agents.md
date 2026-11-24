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
- Intentional differences from the legacy package: the `from_*` helpers
  return `UpSetData`, not pandas objects. Not planned: `generate_*` sample
  data helpers, `query` (use `UpSet(...).subsets` / `.totals`), `add_catplot`.
- Planned: stacked bars (v0.2). Maybe: `style_subsets`.

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
