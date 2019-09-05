Frequently Asked Questions
=============================

.. contents:: Contents
  :depth: 2
  :local:

General
--------

Which version of Python do I need?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

mechanize works on all python versions, python 2 (>= 2.7) and 3 (>= 3.5).


What dependencies does mechanize need?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../requirements.txt

What license does mechanize use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

mechanize is licensed under the `BSD-3-clause
<https://opensource.org/licenses/BSD-3-Clause>`_ license.


Usage
------

I'm not getting the HTML page I expected to see?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :ref:`debugging`.


Is JavaScript supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No, sorry.  See :ref:`jsfaq`

My HTTP response data is truncated?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`mechanize.Browser's` response objects support the `.seek()` method, and
can still be used after `.close()` has been called.  Response data is not
fetched until it is needed, so navigation away from a URL before fetching all
of the response will truncate it.  Call `response.get_data()` before navigation
if you don't want that to happen.

Is there any example code?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Look in the `examples/` directory.  Note that the examples on the forms
page are executable as-is.  Contributions of example code
would be very welcome!


Cookies
-------

Which HTTP cookie protocols does mechanize support?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Netscape and `RFC 2965 <http://www.ietf.org/rfc/rfc2965.txt>`_.  RFC 2965
handling is switched off by default.

What about RFC 2109?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

RFC 2109 cookies are currently parsed as Netscape cookies, and treated
by default as RFC 2965 cookies thereafter if RFC 2965 handling is enabled,
or as Netscape cookies otherwise.


Why don't I have any cookies?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :ref:`cookies`.

My response claims to be empty, but I know it's not?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Did you call `response.read()` (e.g., in a debug statement), then forget
that all the data has already been read?  In that case, you may want to use
`mechanize.response_seek_wrapper`.  `mechanize.Browser` always returns
seekable responses, so it's not necessary to
use this explicitly in that case.

What's the difference between the `.load()` and `.revert()` methods of `CookieJar`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`.load()` *appends* cookies from a file.  `.revert()` discards all
existing cookies held by the `CookieJar` first (but it won't lose any
existing cookies if the loading fails).

Is it threadsafe?
~~~~~~~~~~~~~~~~~~~

See :ref:`threading`.

How do I do `X`?
~~~~~~~~~~~~~~~~~~~~

Refer to the API documentation in :doc:`browser_api`.


Forms
----------

How do I figure out what control names and values to use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`print(form)` is usually all you need.  In your code, things like the
`HTMLForm.items` attribute of :class:`mechanize.HTMLForm` instances can be
useful to inspect forms at runtime.  Note that it's possible to use item labels
instead of item names, which can be useful — use the `by_label` arguments to
the various methods, and the `.get_value_by_label()` / `.set_value_by_label()`
methods on `ListControl`.

What do those `'*'` characters mean in the string representations of list controls?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A `*` next to an item means that item is selected.

What do those parentheses (round brackets) mean in the string representations of list controls?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parentheses `(foo)` around an item mean that item is disabled.

Why doesn't `<some control>` turn up in the data returned by `.click*()` when that control has non-`None` value?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Either the control is disabled, or it is not successful for some other
reason. 'Successful' (see `HTML 4
specification <http://www.w3.org/TR/REC-html40/interact/forms.html#h-17.13.2>`_)
means that the control will cause data to get sent to the server.

Why does mechanize not follow the HTML 4.0 / RFC 1866 standards for `RADIO` and multiple-selection `SELECT` controls?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because by default, it follows browser behaviour when setting the
initially-selected items in list controls that have no items explicitly
selected in the HTML.

Why does `.click()` ing on a button not work for me?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clicking on a `RESET` button doesn't do anything, by design - this is a
library for web automation, not an interactive browser.  Even in an
interactive browser, clicking on `RESET` sends nothing to the server,
so there is little point in having `.click()` do anything special here.

Clicking on a `BUTTON TYPE=BUTTON` doesn't do anything either, also by
design.  This time, the reason is that that `BUTTON` is only in the
HTML standard so that one can attach JavaScript callbacks to its
events.  Their execution may result in information getting sent back to
the server.  mechanize, however, knows nothing about these callbacks,
so it can't do anything useful with a click on a `BUTTON` whose type is
`BUTTON`.

Generally, JavaScript may be messing things up in all kinds of ways.
See :ref:`jsfaq`.

How do I change `INPUT TYPE=HIDDEN` field values (for example, to emulate the effect of JavaScript code)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As with any control, set the control's `readonly` attribute false.

.. code-block:: python

    form.find_control("foo").readonly = False # allow changing .value of control foo
    form.set_all_readonly(False) # allow changing the .value of all controls

I'm having trouble debugging my code.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :ref:`debugging`.

I have a control containing a list of integers.  How do I select the one whose value is nearest to the one I want?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import bisect
    def closest_int_value(form, ctrl_name, value):
        values = map(int, [item.name for item in form.find_control(ctrl_name).items])
        return str(values[bisect.bisect(values, value) - 1])

    form["distance"] = [closest_int_value(form, "distance", 23)]


Miscellaneous
-------------------

I want to see what my web browser is doing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the developer tools for your browser (you may have to install them first).
These provide excellent views into all HTTP requests/responses in the browser.


.. _jsfaq:

JavaScript is messing up my web-scraping. What do I do?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

JavaScript is used in web pages for many purposes -- for example: creating
content that was not present in the page at load time, submitting or
filling in parts of forms in response to user actions, setting cookies,
etc.  mechanize does not provide any support for JavaScript.

If you come across this in a page you want to automate, you have a few
options.  Here they are, roughly in order of simplicity:

  * Figure out what the JavaScript is doing and emulate it in your Python
    code. The simplest case is if the JavaScript is setting some cookies.
    In that case you can inspect the cookies in your browser and emulate
    setting them in mechanize with :meth:`mechanize.Browser.set_simple_cookie()`.

  * More complex is to use your browser developer tools to see exactly what
    requests are sent by the browser and emulate them in mechanize
    by using :class:`mechanize.Request` to create the request manually
    and open it with :meth:`mechanize.Browser.open()`.

  * Third is to use some browser automation framework/library to scrape the
    site instead of using mechanize. These libraries typically drive a headless
    version of a full browser that can execute all JavaScript. They are
    typically much slower than using mechanize and far more resource intensive,
    but do work as a last resort.
