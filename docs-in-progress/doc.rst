=========
mechanize
=========

Stateful programmatic web browsing in Python, after Andy Lester's Perl module
|WWWMechanize|_.

.. |WWWMechanize| replace:: :literal:`WWW::Mechanize`
.. _WWWMechanize: http://search.cpan.org/dist/WWW-Mechanize/

 - ``mechanize.Browser`` is a subclass of ``mechanize.UserAgent``, which is, in
   turn, a subclass of ``urllib2.OpenerDirector`` (in fact, of
   ``mechanize.OpenerDirector``), so:

     - any URL can be opened, not just ``http:``

     - ``mechanize.UserAgent`` offers easy dynamic configuration of user-agent
       features like protocol, cookie, redirection and ``robots.txt`` handling,
       without having to make a new ``OpenerDirector`` each time, e.g.  by
       calling ``build_opener()``.

 - Easy HTML form filling, using `ClientForm`_ interface.

 - Convenient link parsing and following.

 - Browser history (``.back()`` and ``.reload()`` methods).

 - The ``Referer`` HTTP header is added properly (optional).

 - Automatic observance of |robotstxt|

 - Automatic handling of HTTP-Equiv and Refresh.

.. |robotstxt| replace:: :literal:`robots.txt`
.. _robotstxt: http://www.robotstxt.org/wc/norobots.html>

.. _ClientForm: http://wwwsearch.sourceforge.net/ClientForm/


Examples
--------

.. warning::
   This documentation is in need of reorganisation and extension!

The two below are just to give the gist.  There are also some `actual working
examples`_.

.. code-block:: python

    import re
    from mechanize import Browser

    br = Browser()
    br.open("http://www.example.com/")
    # follow second link with element text matching regular expression
    response1 = br.follow_link(text_regex=r"cheese\s*shop", nr=1)
    assert br.viewing_html()
    print br.title()
    print response1.geturl()
    print response1.info()  # headers
    print response1.read()  # body
    response1.close()  # (shown for clarity; in fact Browser does this for you)

    br.select_form(name="order")
    # Browser passes through unknown attributes (including methods)
    # to the selected HTMLForm (from ClientForm).
    br["cheeses"] = ["mozzarella", "caerphilly"]  # (the method here is __setitem__)
    response2 = br.submit()  # submit current form

    # print currently selected form (don't call .submit() on this, use br.submit())
    print br.form

    response3 = br.back()  # back to cheese shop (same data as response1)
    # the history mechanism returns cached response objects
    # we can still use the response, even though we closed it:
    response3.seek(0)
    response3.read()
    response4 = br.reload()  # fetches from server

    for form in br.forms():
	print form
    # .links() optionally accepts the keyword args of .follow_/.find_link()
    for link in br.links(url_regex="python.org"):
	print link
	br.follow_link(link)  # takes EITHER Link instance OR keyword args
	br.back()


You may control the browser's policy by using the methods of
``mechanize.Browser``'s base class, ``mechanize.UserAgent``.  For example:

.. code-block:: python

    br = Browser()
    # Explicitly configure proxies (Browser will attempt to set good defaults).
    # Note the userinfo ("joe:password@") and port number (":3128") are optional.
    br.set_proxies({"http": "joe:password@myproxy.example.com:3128",
		    "ftp": "proxy.example.com",
		    })
    # Add HTTP Basic/Digest auth username and password for HTTP proxy access.
    # (equivalent to using "joe:password@..." form above)
    br.add_proxy_password("joe", "password")
    # Add HTTP Basic/Digest auth username and password for website access.
    br.add_password("http://example.com/protected/", "joe", "password")
    # Don't handle HTTP-EQUIV headers (HTTP headers embedded in HTML).
    br.set_handle_equiv(False)
    # Ignore robots.txt.  Do not do this without thought and consideration.
    br.set_handle_robots(False)
    # Don't handle cookies
    br.set_cookiejar()
    # Supply your own mechanize.CookieJar (NOTE: cookie handling is ON by
    # default: no need to do this unless you have some reason to use a
    # particular cookiejar)
    br.set_cookiejar(cj)
    # Log information about HTTP redirects and Refreshes.
    br.set_debug_redirects(True)
    # Log HTTP response bodies (ie. the HTML, most of the time).
    br.set_debug_responses(True)
    # Print HTTP headers.
    br.set_debug_http(True)

    # To make sure you're seeing all debug output:
    logger = logging.getLogger("mechanize")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

    # Sometimes it's useful to process bad headers or bad HTML:
    response = br.response()  # this is a copy of response
    headers = response.info()  # currently, this is a mimetools.Message
    del headers["Content-type"]  # get rid of (possibly multiple) existing headers
    headers["Content-type"] = "text/html; charset=utf-8"
    response.set_data(response.get_data().replace("<!---", "<!--"))


mechanize exports the complete interface of ``urllib2``:

.. code-block:: python

    import mechanize
    response = mechanize.urlopen("http://www.example.com/")
    print response.read()


so anything you would normally import from ``urllib2`` can (and should, by
preference, to insulate you from future changes) be imported from mechanize
instead.  In many cases if you import an object from mechanize it will be the
very same object you would get if you imported from urllib2.  In many other
cases, though, the implementation comes from mechanize, either because bug
fixes have been applied or the functionality of urllib2 has been extended in
some way.


Compatibility
-------------

These notes explain the relationship between mechanize, ClientCookie,
``cookielib`` and ``urllib2``, and which to use when.  If you're just using
mechanize, and not any of those other libraries, you can ignore this section.

  1. mechanize works with Python 2.3, Python 2.4 and Python 2.5.

  #. ClientCookie is no longer maintained as a separate package.  The code is
     now part of mechanize, and its interface is now exported through module
     mechanize (since mechanize 0.1.0).  Old code can simply be changed to
     ``import mechanize as ClientCookie`` and should continue to work.

  #. The cookie handling parts of mechanize are in Python 2.4 standard library
     as module ``cookielib`` and extensions to module ``urllib2``.

.. important::

  The following are the ONLY cases where ``mechanize`` and
  ``urllib2`` code are intended to work together.  For all other code, use
  mechanize *exclusively*: do NOT mix use of mechanize and ``urllib2``!

  1. Handler classes that are missing from 2.4's ``urllib2``
     (e.g. ``HTTPRefreshProcessor``, ``HTTPEquivProcessor``,
     ``HTTPRobotRulesProcessor``) may be used with the ``urllib2`` of Python
     2.4 or newer.  There are not currently any functional tests for this in
     mechanize, however, so this feature may be broken.

  #. If you want to use ``mechanize.RefreshProcessor`` with Python >= 2.4's
     ``urllib2``, you must also use ``mechanize.HTTPRedirectHandler``.

  #. ``mechanize.HTTPRefererProcessor`` requires special support from
      ``mechanize.Browser``, so cannot be used with vanilla ``urllib2``.

  #. ``mechanize.HTTPRequestUpgradeProcessor`` and
     ``mechanize.ResponseUpgradeProcessor`` are not useful outside of
     mechanize.

  #. Request and response objects from code based on ``urllib2`` work with
     mechanize, and vice-versa.

  #. The classes and functions exported by mechanize in its public interface
     that come straight from ``urllib2`` (e.g. ``FTPHandler``, at the time of
     writing) do work with mechanize (duh ;-).  Exactly which of these classes
     and functions come straight from ``urllib2`` without extension or
     modification will change over time, though, so don't rely on it; instead,
     just import everything you need from mechanize, never from ``urllib2``.
     The exception is usage as described in the first item in this list, which
     is explicitly OK (though not well tested ATM), subject to the other
     restrictions in the list above.


Documentation
-------------

Full documentation is in the docstrings.

The documentation in the web pages is in need of reorganisation at the moment,
after the merge of ClientCookie into mechanize.


Credits
-------

Thanks to all the too-numerous-to-list people who reported bugs and provided
patches.  Also thanks to Ian Bicking, for persuading me that a ``UserAgent``
class would be useful, and to Ronald Tschalar for advice on Netscape cookies.

A lot of credit must go to Gisle Aas, who wrote libwww-perl, from which large
parts of mechanize originally derived, and Andy Lester for the original,
|WWWMechanize|_.  Finally, thanks to the (coincidentally-named) Johnny Lee for
the MSIE CookieJar Perl code from which mechanize's support for that is
derived.


Todo
----

Contributions welcome!

Documentation
~~~~~~~~~~~~~

  - Docs need reworking since merge with ClientCookie.  Comments are especially
    welcome here!

     - Move install / FAQ / download to separate pages!

     - Website menu is lame.  Pick something better.  Headings are badly sized,
       too.

     - Publish the docstrings on the website as HTML API docs.

     - Integrate / rework non-docstring ClientCookie / mechanize docs.

     - Non-docstring mechanize docs need extending.

     - Consider structure of non-docstring docs: e.g. split into tutorial / ref
       sections?

     - Maybe change the format docs are written in, so can generate in multiple
       formats (one page / multipage HTML, maybe PDF, man, info) and integrate
       docstring and non-docstring docs.

  - Note BeautifulSoup 3.0 doesn't work yet.

  - Document use of BeautifulSoup (RobustFactory).

  - Document means of processing response on ad-hoc basis with .set_response()
    - e.g. to fix bad encoding in Content-type header or clean up bad HTML.

  - Add example to documentation showing can pass None as handle arg to
    ``mechanize.UserAgent`` methods and then .add_handler() if need to give it
    a specific handler instance to use for one of the things it UserAgent
    already handles.  Hmm, think this contradicts docs ATM!  And is it better
    to do this a different way...??

  - Add more functional tests.

  - Auth and proxies.


Code
~~~~

This is *very* roughly in order of priority

  - Topological sort for handlers, instead of .handler_order attribute.  Add
    new build_opener and deprecate the old one?

  - Use RFC 3986 URL absolutization.

  - Test ``.any_response()`` two handlers case: ordering.

  - Test referer bugs (frags and don't add in redirect unless orig req had
    Referer)

  - Proper XHTML support!

  - Fix BeautifulSoup support to use a single BeautifulSoup instance per page.

  - Test BeautifulSoup support better / fix encoding issue.

  - Support BeautifulSoup 3.

  - Add another History implementation or two and finalise interface.

  - History cache expiration.

  - Investigate possible leak further (see Balazs Ree's list posting).

  - Make ``EncodingFinder`` public, I guess (but probably improve it first).
    (For example: support Mark Pilgrim's universal encoding detector?)

  - Add two-way links between BeautifulSoup &amp; ClientForm object models.

  - In 0.2: switch to Python unicode strings everywhere appropriate (HTTP level
    should still use byte strings, of course).

  - ``clean_url()``: test browser behaviour.  I *think* this is correct...

  - Figure out the Right Thing (if such a thing exists) for %-encoding.

  - How do IRIs fit into the world?

  - IDNA -- must read about security stuff first.

  - Unicode support in general.

  - Provide per-connection access to timeouts.

  - Keep-alive / connection caching.

  - Pipelining??

  - Content negotiation.

  - gzip transfer encoding (there's already a handler for this in mechanize,
    but it's poorly implemented ATM).

  - proxy.pac parsing (I don't think this needs JS interpretation)


Getting mechanize
-----------------

You can install the `old-fashioned way`_, or using EasyInstall_.  I recommend
the latter even though EasyInstall is still in alpha, because it will
automatically ensure you have the necessary dependencies, downloading if
necessary.



.. _`old-fashioned way`: Download_ 

.. _EasyInstall: http://peak.telecommunity.com/DevCenter/EasyInstall


`Subversion (SVN) access`__ is also available.

__ Subversion_

Since EasyInstall is new, I include some instructions below, but mechanize
follows standard EasyInstall / ``setuptools`` conventions, so you should refer
to the Easyinstall_ and |setuptools|_ documentation if you need more detailed
or up-to-date instructions.

.. |setuptools| replace:: :literal:`setuptools`
.. _setuptools: http://peak.telecommunity.com/DevCenter/setuptools


EasyInstall / setuptools
------------------------

The benefit of EasyInstall and the new ``setuptools``-supporting ``setup.py``
is that they grab all dependencies for you.  Also, using EasyInstall is a
one-liner for the common case, to be compared with the usual
download-unpack-install cycle with ``setup.py``.

*You need EasyInstall version 0.6a8 or newer.*

Using EasyInstall to download and install mechanize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  1. `Install easy_install`__ (you need version 0.6a8 or newer)

__ http://peak.telecommunity.com/DevCenter/EasyInstall#installing-easy-install

  2. ``easy_install mechanize``

If you're on a Unix-like OS, you may need root permissions for that last step
(or see the `EasyInstall documentation
<http://peak.telecommunity.com/DevCenter/EasyInstall>` for other installation
options).

If you already have mechanize installed as a `Python Egg
<http://peak.telecommunity.com/DevCenter/PythonEggs>` (as you do if you
installed using EasyInstall, or using ``setup.py install`` from mechanize
0.0.10a or newer), you can upgrade to the latest version using::

    easy_install --upgrade mechanize

You may want to read up on the ``-m`` option to ``easy_install``, which lets
you install multiple versions of a package.

Using EasyInstall to download and install the latest in-development (SVN HEAD) version of mechanize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    easy_install "mechanize==dev"

Note that that will not necessarily grab the SVN versions of dependencies, such
as ClientForm: It will use SVN to fetch dependencies if and only if the SVN
HEAD version of mechanize declares itself to depend on the SVN versions of
those dependencies; even then, those declared dependencies won't necessarily be
on SVN HEAD, but rather a particular revision.  If you want SVN HEAD for a
dependency project, you should ask for it explicitly by running ``easy_install
"projectname=dev"`` for that project.

Note also that you can still carry on using a plain old SVN checkout as usual
if you like (optionally in conjunction with |setuppydevelop|_ |--| this is
particularly useful on Windows, since it functions rather like symlinks).

Using setup.py from a .tar.gz, .zip or an SVN checkout to download and install mechanize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``setup.py`` should correctly resolve and download dependencies::

    python setup.py install

Or, to get access to the same options that ``easy_install`` accepts, use the
``easy_install`` distutils command instead of ``install`` (see ``python
setup.py --help easy_install``)::

    python setup.py easy_install mechanize


.. |setuppydevelop| replace:: :literal:`setup.py develop`
.. _setuppydevelop: 

Using setup.py to install mechanize for development work on mechanize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Note: this section is only useful for people who want to change mechanize*: It
is not useful to do this if all you want is to `keep up with SVN <./#svnhead>`.

For development of mechanize using EasyInstall (see the `setuptools
<http://peak.telecommunity.com/DevCenter/setuptools>` docs for details), you
have the option of using the ``develop`` distutils command.  This is
particularly useful on Windows, since it functions rather like symlinks.  Get
the mechanize source, then::

    python setup.py develop

Note that after every ``svn update`` on a ``develop``-installed project, you
should run ``setup.py develop`` to ensure that project's dependencies are
updated if required.

Also note that, currently, if you also use the ``develop`` distutils command on
the <em>dependencies</em> of mechanize (*viz*, ClientForm, and optionally
``BeautifulSoup``) to keep up with SVN, you must run ``setup.py develop`` for
each dependency of mechanize before running it for mechanize itself.  As a
result, in this case it's probably simplest to just set up your ``sys.path``
manually rather than using ``setup.py develop``.

One convenient way to get the latest source is::

    easy_install --editable --build-directory mybuilddir "mechanize==dev"


Download
--------

All documentation (including this web page) is included in the distribution.

This is a stable release.

Development release
~~~~~~~~~~~~~~~~~~~

@{version = "0.1.4b"}
 - <a href="./src/mechanize-@(version).tar.gz">mechanize-@(version).tar.gz</a>
 - <a href="./src/mechanize-@(version).zip">mechanize-@(version).zip</a>
 - <a href="./src/ChangeLog.txt">Change Log</a> (included in distribution)
 - <a href="./src/">Older versions.</a>

For old-style installation instructions, see the INSTALL file included
in the distribution.  Better, <a href="./#download">use
EasyInstall</a>.


Subversion
----------

The `Subversion (SVN)`_ trunk is
`http://codespeak.net/svn/wwwsearch/mechanize/trunk`__.  so to check out the
source:

__ http://codespeak.net/svn/wwwsearch/mechanize/trunk#egg=mechanize-dev

.. _`Subversion (SVN)`: http://subversion.tigris.org/

::

    svn co http://codespeak.net/svn/wwwsearch/mechanize/trunk mechanize


.. _`actual working examples`:

Tests and examples
------------------

Examples
~~~~~~~~

The ``examples`` directory in the `source packages`_ contains a couple of
silly, but working, scripts to demonstrate basic use of the module.  Note that
it's in the nature of web scraping for such scripts to break, so don't be too
suprised if that happens |--| do let me know, though!

.. _`source packages`: Download_

It's worth knowing also that the examples on the `ClientForm web page`_ are
useful for mechanize users, and are now real run-able scripts rather than just
documentation.

.. _`ClientForm web page`: ClientForm_


Functional tests
~~~~~~~~~~~~~~~~

To run the functional tests (which <strong>do</strong> access the network), run
the following command::

    python functional_tests.py

Unit tests
~~~~~~~~~~

Note that ClientForm (a dependency of mechanize) has its own unit tests, which
must be run separately.

To run the unit tests (none of which access the network), run the following
command::

    python test.py

This runs the tests against the source files extracted from the package.  For
help on command line options::

    python test.py --help


See also
--------

There are several wrappers around mechanize designed for functional
testing of web applications:

  - |zopetestbrowser|_ (or |ZopeTestBrowser|_, the standalone version).

  - `twill <http://www.idyll.org/~t/www-tools/twill.html>`_.

.. |zopetestbrowser| replace:: :literal:`zope.testbrowser`
.. _zopetestbrowser: http://cheeseshop.python.org/pypi?:action=display&name=zope.testbrowser

.. |ZopeTestBrowser| replace:: :literal:`ZopeTestBrowser`
.. ZopeTestBrowser_: http://cheeseshop.python.org/pypi?%3Aaction=display&name=ZopeTestbrowser

Richard Jones' `webunit <http://mechanicalcat.net/tech/webunit/>`_ (this is not
the same as Steven Purcell's `code of the same name`_.  webunit and mechanize
are quite similar.  On the minus side, webunit is missing things like browser
history, high-level forms and links handling, thorough cookie handling, refresh
redirection, adding of the Referer header, observance of ``robots.txt`` and
easy extensibility.  On the plus side, webunit has a bunch of utility functions
bound up in its WebFetcher class, which look useful for writing tests (though
they'd be easy to duplicate using mechanize).  In general, webunit has more of
a frameworky emphasis, with aims limited to writing tests, where mechanize and
the modules it depends on try hard to be general-purpose libraries.

.. _`code of the same name`: http://webunit.sourceforge.net/

There are many related links in the `General FAQ`_ page, too.

.. _`General FAQ`: ../bits/GeneralFAQ.html


FAQs - pre install
------------------

  - Which version of Python do I need?

    2.3 or above.

  - What else do I need?

    mechanize depends on ClientForm_.  The ``setup.py`` script also declares a
    dependency on BeautifulSoup_, but there is no true dependency: the
    declaration is there only to avoid confusing people who don't realise that
    mechanize is not compatible with BeautifulSoup version 3 |--| only
    BeautifulSoup version 2 is currently supported.  A future version of
    mechanize will support BeautifulSoup version 3.

  - The versions of those required modules are listed in the ``setup.py`` for
    mechanize (included with the download).  The dependencies are automatically
    fetched by EasyInstall_ (or by downloading_ a mechanize source package and
    running ``python setup.py install``).  If you like you can fetch and
    install them manually, instead |--| see the ``INSTALL.txt`` file (included
    with the distribution).

  - Which license?

    mechanize is dual-licensed: you may pick either the `BSD license`_, or the
    ZPL 2.1 (both are included in the distribution).


.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _downloading: Download_
.. _`BSD license`: http://www.opensource.org/licenses/bsd-license.php
.. _`ZPL 2.1`: http://www.zope.org/Resources/ZPL


FAQs - usage
------------

  - I'm **sure** this page is HTML, why does ``mechanize.Browser`` think
    otherwise?

.. code-block:: python

    b = mechanize.Browser(
	# mechanize's XHTML support needs work, so is currently switched off.  If
	# we want to get our work done, we have to turn it on by supplying a
	# mechanize.Factory (with XHTML support turned on):
	factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
	)

I prefer questions and comments to be sent to the `mailing list`_ rather than
direct to me.

.. _`mailing list`: http://lists.sourceforge.net/lists/listinfo/wwwsearch-general


.. |--| unicode:: U+2013
