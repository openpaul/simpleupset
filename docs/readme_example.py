"""Generate the example image shown at the top of the README.

    uv run python docs/readme_example.py

The data is a made-up survey (fixed seed): which languages each respondent
uses, and their role.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from simpleupset import upsetplot  # noqa: E402

OUT = Path(__file__).parent / "_static" / "readme-example.png"

rng = np.random.default_rng(7)
roles = rng.choice(["student", "researcher", "engineer"], size=300, p=[0.3, 0.4, 0.3])
use = {
    "Python": {"student": 0.85, "researcher": 0.8, "engineer": 0.75},
    "SQL": {"student": 0.3, "researcher": 0.35, "engineer": 0.8},
    "R": {"student": 0.35, "researcher": 0.5, "engineer": 0.1},
    "Julia": {"student": 0.05, "researcher": 0.15, "engineer": 0.03},
}
languages = {
    lang: [i for i, role in enumerate(roles) if rng.random() < p[role]]
    for lang, p in use.items()
}

fig = plt.figure()
upsetplot(
    languages,
    fig=fig,
    stack_by=dict(enumerate(roles)),
    stack_colors={"student": "#9ecae1", "researcher": "#4292c6", "engineer": "#08519c"},
    sort_by="cardinality",
    min_subset_size=3,
    show_counts=True,
)
OUT.parent.mkdir(exist_ok=True)
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"wrote {OUT}")
