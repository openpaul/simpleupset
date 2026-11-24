Installation
============

simpleupset is installed from GitHub. Pin a release tag (see the
`tags <https://github.com/openpaul/simpleupset/tags>`_) so upgrades are
deliberate; the API may change before 1.0.

uv
--

.. code-block:: bash

   uv add git+https://github.com/openpaul/simpleupset --tag v0.1.5

or in ``pyproject.toml``:

.. code-block:: toml

   [project]
   dependencies = ["simpleupset"]

   [tool.uv.sources]
   simpleupset = { git = "https://github.com/openpaul/simpleupset", tag = "v0.1.5" }

pixi
----

.. code-block:: bash

   pixi add --pypi "simpleupset @ git+https://github.com/openpaul/simpleupset@v0.1.5"

or in ``pixi.toml``:

.. code-block:: toml

   [pypi-dependencies]
   simpleupset = { git = "https://github.com/openpaul/simpleupset", tag = "v0.1.5" }

pip
---

.. code-block:: bash

   pip install "git+https://github.com/openpaul/simpleupset@v0.1.5"
