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


The Response
---------------

Response objects in mechanize are `seek()` able :class:`file`-like objects that support
some additional methods, depending on the protocol used for the connection. The documentation
below is for HTTP(s) responses, as these are the most common.

Additional methods present for HTTP responses:

.. class:: HTTPResponse

    .. attribute:: code

        The HTTP status code

    .. method:: getcode()
        
        Return HTTP status code

    .. method:: geturl()

        Return the URL of the resource retrieved, commonly used to determine if
        a redirect was followed

    .. method:: get_all_header_names(normalize=True)

        Return a list of all headers names. When `normalize` is `True`, the
        case of the header names is normalized.

    .. method:: get_all_header_values(name, normalize=True)

        Return a list of all values for the specified header `name` (which is
        case-insensitive. Since headers in HTTP can be specified multiple
        times, the returned value is always a list. See
        :meth:`rfc822.Message.getheaders`.

    .. method:: info()

        Return the headers of the response as a :class:`rfc822.Message`
        instance.

    .. method:: __getitem__(header_name)

        Return the *last* HTTP Header matching the specified name as string. 
        mechanize Response object act like dictionaries for convenient access
        to header values. For example: :code:`response['Date']`. You can access
        header values using the header names, case-insensitively. Note that
        when more than one header with the same name is present, only the value
        of the last header is returned, use :meth:`get_all_header_values()` to
        get the values of all headers.

    .. method:: get(header_name, default=None):
        
        Return the header value for the specified `header_name` or `default` if
        the header is not present. See :meth:`__getitem__`.

Miscellaneous
-----------------

.. autoclass:: mechanize.Link
   :members:

.. autoclass:: mechanize.History
   :members:

.. automodule:: mechanize._html
   :members: content_parser
