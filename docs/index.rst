simpleupset
===========

UpSet plots for Python with a small API: pass a dict of sets (or lists),
get a matplotlib figure.

.. code-block:: python

   from simpleupset import plot

   plot({"a": [1, 2, 3, 4], "b": [2, 3, 5], "c": [4, 5, 6]})

The API follows the legacy `UpSetPlot <https://github.com/jnothman/UpSetPlot>`_
package, so ``UpSet(data, ...).plot()`` and ``plot(data, ...)`` accept the
same arguments and return the same dict of axes.

.. toctree::
   :maxdepth: 2

   install
   examples
   api
