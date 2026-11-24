API reference
=============

Plotting
--------

.. autofunction:: simpleupset.plot

.. autoclass:: simpleupset.UpSet
   :members: plot

Input helpers
-------------

All inputs are normalised to :class:`~simpleupset.UpSetData`. These mirror
the constructors of the legacy package but return ``UpSetData`` instead of
a pandas object.

.. autofunction:: simpleupset.from_contents

.. autofunction:: simpleupset.from_memberships

.. autofunction:: simpleupset.from_indicators

.. autoclass:: simpleupset.UpSetData
   :members: category_totals, subsets, sort_categories

.. autoclass:: simpleupset.Subset
   :members: degree
