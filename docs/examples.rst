Examples
========

Each example is small enough to check by hand. The table under the input
lists what the plot should show. Each bar counts the elements that are in
**exactly** that combination of sets (exclusive intersections), so the bar
heights always add up to the number of distinct elements.

Two sets
--------

Input: ``a = {1, 2, 3}``, ``b = {3, 4}``.

============  ========  ====
Intersection  Elements  Size
============  ========  ====
a only        1, 2      2
b only        4         1
a and b       3         1
============  ========  ====

Set sizes: a = 3, b = 2.

.. plot::

   from simpleupset import upsetplot

   upsetplot({"a": {1, 2, 3}, "b": {3, 4}}, show_counts=True)

Dict of lists
-------------

Lists work like sets; duplicates are ignored.

==============  ========  ====
Intersection    Elements  Size
==============  ========  ====
a and b         2, 3      2
b and c         5, 21     2
a only          1         1
b only          19        1
c only          30        1
a and c         4         1
==============  ========  ====

Set sizes: b = 5, a = 4, c = 4.

.. plot::

   from simpleupset import upsetplot

   items = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
   upsetplot(items, sort_by="cardinality", show_counts=True)

Nested sets with percentages
----------------------------

``even`` and ``small`` are subsets of ``all``, so every bar includes ``all``.
Percentages are relative to the 6 elements.

===================  ========  ====  =====
Intersection         Elements  Size  Share
===================  ========  ====  =====
all only             3, 5      2     33.3%
all, even            4, 6      2     33.3%
all, small           1         1     16.7%
all, even, small     2         1     16.7%
===================  ========  ====  =====

Set sizes: all = 6, even = 3, small = 2.

.. plot::

   from simpleupset import upsetplot

   sets = {"all": [1, 2, 3, 4, 5, 6], "even": [2, 4, 6], "small": [1, 2]}
   upsetplot(sets, show_counts=True, show_percentages=True)

Vertical orientation
--------------------

Same data as *Dict of lists*, rotated.

.. plot::

   from simpleupset import upsetplot

   items = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
   upsetplot(items, orientation="vertical", sort_by="cardinality", show_counts=True)

Filtering
---------

``min_degree=2`` keeps only intersections of two or more sets. Same data as
*Dict of lists*: the bars are ``a and b`` (2), ``a and c`` (1) and
``b and c`` (2). Set sizes are unchanged.

.. plot::

   from simpleupset import upsetplot

   items = {"a": [1, 2, 3, 4], "b": [2, 3, 5, 19, 21], "c": [4, 5, 21, 30]}
   upsetplot(items, min_degree=2, show_counts=True)

Weighted memberships
--------------------

One list of sets per element, with a weight per element. Bars show the
summed weight instead of a count.

============  ===================  ====
Intersection  Weights              Size
============  ===================  ====
x only        1.5 + 0.5            2
y only        4                    4
x and y       2                    2
============  ===================  ====

Set sizes: x = 4, y = 6.

.. plot::

   from simpleupset import from_memberships, upsetplot

   data = from_memberships(
       [["x"], ["x", "y"], ["y"], ["x"]],
       data=[1.5, 2.0, 4.0, 0.5],
   )
   upsetplot(data, show_counts=True)

Legacy UpSetPlot input
----------------------

A pandas Series with a boolean MultiIndex, as built by the legacy
``upsetplot.from_memberships``, is plotted as-is. pandas is only needed if
you pass pandas objects.

============  ====
Intersection  Size
============  ====
cat1 only     5
cat1, cat2    3
cat2 only     2
============  ====

Set sizes: cat1 = 8, cat2 = 5.

.. plot::

   import pandas as pd
   from simpleupset import UpSet

   index = pd.MultiIndex.from_tuples(
       [(True, False), (True, True), (False, True)], names=["cat1", "cat2"]
   )
   series = pd.Series([5, 3, 2], index=index)
   UpSet(series, sort_by="cardinality", show_counts=True).plot()
