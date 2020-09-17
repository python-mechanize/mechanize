mechanize - Automate interaction with HTTP web servers
##########################################################

|pypi| |build|

.. contents::


Major features
-----------------

Stateful programmatic web browsing in Python

- The browser class `mechanize.Browser` implements the
  interface of `urllib2.OpenerDirector`, so any URL can
  be opened not just `http`.

- Easy HTML form filling.

- Convenient link parsing and following.

- Browser history (`.back()` and `.reload()` methods).

- The `Referer` HTTP header is added properly (optional).

- Automatic observance of `robots.txt <http://www.robotstxt.org/wc/norobots.html>`_.

- Automatic handling of HTTP-Equiv and Refresh.


Installation
-----------------

To install for normal usage:

.. code-block:: bash

    pip3 install mechanize

To install for development:

.. code-block:: bash

    git clone https://github.com/python-mechanize/mechanize.git
    cd mechanize
    pip3 install -e .

To install manually, simply add the `mechanize` sub-directory somewhere on your
`PYTHONPATH`.


Documentation
---------------

See https://mechanize.readthedocs.io/en/latest/

Credits
-----------------

python-mechanize was the creation of John J. Lee. Maintenance was taken over by
Kovid Goyal in 2017.

Much of the code was originally derived from the work of the following people:

- Gisle Aas -- [libwww-perl]

- Jeremy Hylton (and many others) -- [urllib2]

- Andy Lester -- [WWW::Mechanize]

- Johnny Lee (coincidentally-named) -- MSIE CookieJar Perl code from which
  mechanize's support for that is derived.

Also:

- Gary Poster and Benji York at Zope Corporation -- contributed significant
  changes to the HTML forms code

- Ronald Tschalar -- provided help with Netscape cookies

Thanks also to the many people who have contributed bug reports and
patches.

.. |pypi| image:: https://img.shields.io/pypi/v/mechanize.svg?label=version
    :target: https://pypi.python.org/pypi/mechanize
    :alt: Latest version released on PyPi

.. |build| image:: https://dev.azure.com/divok/mechanize/_apis/build/status/python-mechanize.mechanize?branchName=master
    :target: https://dev.azure.com/divok/mechanize/_build/latest?definitionId=3&branchName=master
    :alt: Build status of the master branch
