"""Image regression tests: each case is rendered and compared to a baseline PNG.

After an intended visual change, regenerate and review the baselines:

    uv run pytest tests/test_images.py --regen-images
    git diff --stat tests/baseline

On failure the rendered image and a diff are written to tests/image_results/.

Text rendering changes between matplotlib minor versions, so baselines are
tied to the version that made them (tests/baseline/matplotlib-version.txt).
On another version the tests skip, or fail if REQUIRE_IMAGE_TESTS is set
(CI sets it on one job so image coverage cannot silently disappear).
"""

import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.testing
import pytest
from matplotlib.testing.compare import compare_images

from simpleupset import from_memberships, upsetplot

HERE = Path(__file__).parent
BASELINE = HERE / "baseline"
RESULTS = HERE / "image_results"
VERSION_FILE = BASELINE / "matplotlib-version.txt"
MPL_VERSION = ".".join(matplotlib.__version__.split(".")[:2])

# RMS over 0-255 pixel values. An identical render is 0; a faint shading change
# (alpha 0.05 -> 0.07) is ~1.4; a 4% wider bar is ~16.
TOLERANCE = 1.0

THREE = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
STACK_ITEMS = {"a": [1, 2, 3, 4, 6, 7], "b": [2, 3, 5, 6, 19, 21], "c": [4, 5, 21, 30, 31]}
LONG_LABELS = {
    "selected subset": range(0, 40),
    "connected components": range(30, 60),
    "isolated nodes": [*range(55, 70), 1, 2, 3],
}

CASES = {
    "basic": lambda: upsetplot(THREE, show_counts=True),
    "vertical": lambda: upsetplot(THREE, orientation="vertical", show_counts=True),
    "long_labels": lambda: upsetplot(LONG_LABELS, show_counts=True),
    "percentages": lambda: upsetplot(
        {"all": range(1, 7), "even": [2, 4, 6], "small": [1, 2]},
        show_counts=True,
        show_percentages=True,
    ),
    "weighted": lambda: upsetplot(
        from_memberships([["x"], ["x", "y"], ["y"]], data=[1.5, 2.25, 4]),
        show_counts=True,
    ),
    "styled": lambda: upsetplot(
        THREE,
        facecolor="tab:blue",
        other_dots_color=0.3,
        with_lines=False,
        sort_by="cardinality",
    ),
    "empty_subsets": lambda: upsetplot(
        {"a": [1], "b": [2], "c": [1, 2]}, include_empty_subsets=True
    ),
    "stacked": lambda: upsetplot(
        STACK_ITEMS, stack_by=lambda e: "odd" if e % 2 else "even", show_counts=True
    ),
    "stacked_vertical": lambda: upsetplot(
        STACK_ITEMS,
        orientation="vertical",
        stack_by=lambda e: ["low", "mid", "high"][e % 3],
        stack_colors={"low": "#9ecae1", "mid": "#4292c6", "high": "#08519c"},
        show_counts=True,
    ),
}


def _check_baseline_version(regen: bool) -> None:
    if regen:
        BASELINE.mkdir(exist_ok=True)
        VERSION_FILE.write_text(MPL_VERSION + "\n")
        return
    made_with = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "unknown"
    if made_with != MPL_VERSION:
        message = (
            f"baselines were made with matplotlib {made_with}, installed is "
            f"{MPL_VERSION}; regenerate with --regen-images on the new version"
        )
        if os.environ.get("REQUIRE_IMAGE_TESTS"):
            pytest.fail(message, pytrace=False)
        pytest.skip(message)


@pytest.mark.parametrize("name", CASES)
def test_image(name, request):
    regen = request.config.getoption("--regen-images")
    _check_baseline_version(regen)
    with plt.rc_context():
        matplotlib.testing.set_font_settings_for_testing()
        CASES[name]()
        fig = plt.gcf()
        RESULTS.mkdir(exist_ok=True)
        actual = RESULTS / f"{name}.png"
        fig.savefig(actual, dpi=72)

    expected = BASELINE / f"{name}.png"
    if regen:
        expected.write_bytes(actual.read_bytes())
        actual.unlink()
        pytest.skip(f"baseline regenerated: {expected.relative_to(HERE.parent)}")

    if not expected.exists():
        pytest.fail(f"no baseline for {name!r}; run pytest --regen-images")
    error = compare_images(str(expected), str(actual), tol=TOLERANCE)
    if error:
        pytest.fail(f"{error}\nsee {RESULTS}", pytrace=False)
    actual.unlink()
