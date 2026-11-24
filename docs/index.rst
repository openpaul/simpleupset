simpleupset
===========

UpSet plots for Python with a small API: pass a dict of sets (or lists),
get a matplotlib figure.

Source code, issues and releases: `github.com/openpaul/simpleupset
<https://github.com/openpaul/simpleupset>`_.

.. code-block:: python

   from simpleupset import upsetplot

   upsetplot({"a": [1, 2, 3, 4], "b": [2, 3, 5], "c": [4, 5, 6]})

In a script, call ``plt.show()`` afterwards. Jupyter shows the plot on its
own; VS Code notebooks may need ``plt.show()`` too. In notebooks, end the
line with ``;`` to hide the returned dict of axes.

The API follows the legacy `UpSetPlot <https://github.com/jnothman/UpSetPlot>`_
package: ``UpSet(data, ...).plot()`` takes the same arguments and returns the
same dict of axes, and ``plot`` is kept as an alias of ``upsetplot``.

.. toctree::
   :maxdepth: 2

   install
   examples
   api
