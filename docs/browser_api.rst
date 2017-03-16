.. _browser_api:

Browser API
======================================================

.. module:: mechanize._mechanize
    :synopsis: The API for mechanize browsers
    
API documentation for the mechanize :class:`Browser` object.
You can create a mechanize :class:`Browser` instance as:

.. code-block:: python

    from mechanize import Browser
    br = Browser()

.. contents:: Contents

The Browser
----------------

.. autoclass:: mechanize.Browser
   :members:
   :inherited-members:

The Request
--------------
.. autoclass:: mechanize.Request
   :members:
   :inherited-members:

Miscellaneous
-----------------

.. autoclass:: mechanize.Link
   :members:

.. autoclass:: mechanize.History
   :members:

.. automodule:: mechanize._html
   :members: content_parser
