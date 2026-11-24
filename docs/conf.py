from importlib.metadata import version as _version

project = "simpleupset"
author = "openpaul"
release = _version("simpleupset")
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "matplotlib.sphinxext.plot_directive",
]

html_theme = "furo"
html_title = f"simpleupset {release}"
exclude_patterns = ["_build"]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_numpy_docstring = True

plot_include_source = True
plot_html_show_source_link = False
plot_html_show_formats = False
plot_formats = [("png", 100)]
plot_rcparams = {"savefig.bbox": "tight"}
