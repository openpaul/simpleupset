import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--regen-images",
        action="store_true",
        help="rewrite the baseline images in tests/baseline instead of comparing",
    )


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")
