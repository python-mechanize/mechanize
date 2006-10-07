==================
mechanize handlers
==================

.. warning::
   This documentation is in need of reorganisation!

This page is the old ClientCookie documentation.  It deals with operation on
the level of urllib2 `Handler` objects, and also with adding headers,
debugging, and cookie handling.  Documentation for the higher-level
browser-style interface is `elsewhere`_.

.. _elsewhere: ./mechanize


.. _examples:

Examples
--------

.. code-block:: python

    import mechanize
    response = mechanize.urlopen("http://foo.bar.com/")

This function behaves identically to `urllib2.urlopen()`, except that it deals
with cookies automatically.

Here is a more complicated example, involving `Request` objects (useful if you
want to pass `Request` objects around, add headers to them, etc.):

.. code-block:: python

    import mechanize
    request = mechanize.Request("http://www.acme.com/")
    # note we're using the urlopen from mechanize, not urllib2
    response = mechanize.urlopen(request)
    # let's say this next request requires a cookie that was set in response
    request2 = mechanize.Request("http://www.acme.com/flying_machines.html")
    response2 = mechanize.urlopen(request2)

    print response2.geturl()
    print response2.info()  # headers
    print response2.read()  # body (readline and readlines work too)

(The above example would also work with `urllib2.Request` objects too, since
`mechanize.HTTPRequestUpgradeProcessor` knows about that class, but don't if
you can avoid it, because this is an obscure hack for compatibility purposes
only).

In these examples, the workings are hidden inside the `mechanize.urlopen()`
function, which is an extension of `urllib2.urlopen()`.  Redirects, proxies and
cookies are handled automatically by this function (note that you may need a
bit of configuration to get your proxies correctly set up: see `urllib2`
documentation).

Cookie processing (etc.) is handled by processor objects, which are an
extension of `urllib2`'s handlers: `HTTPCookieProcessor`,
`HTTPRefererProcessor`, `SeekableProcessor` etc.  They are used like any other
handler.  There is quite a bit of other `urllib2`-workalike code, too.  Note:
This duplication has gone away in Python 2.4, since 2.4's `urllib2` contains
the processor extensions from mechanize, so you can simply use mechanize's
processor classes direct with 2.4's `urllib2`; also, mechanize's cookie
functionality is included in Python 2.4 as module `cookielib` and
`urllib2.HTTPCookieProcessor`.

There is also a `urlretrieve()` function, which works like
`urllib.urlretrieve()`.

An example at a slightly lower level shows how the module processes cookies
more clearly:

.. code-block:: python

    # Don't copy this blindly!  You probably want to follow the examples
    # above, not this one.
    import mechanize

    # Build an opener that *doesn't* automatically call .add_cookie_header()
    # and .extract_cookies(), so we can do it manually without interference.
    class NullCookieProcessor(mechanize.HTTPCookieProcessor):
	def http_request(self, request): return request
	def http_response(self, request, response): return response
    opener = mechanize.build_opener(NullCookieProcessor)

    request = mechanize.Request("http://www.acme.com/")
    response = mechanize.urlopen(request)
    cj = mechanize.CookieJar()
    cj.extract_cookies(response, request)
    # let's say this next request requires a cookie that was set in response
    request2 = mechanize.Request("http://www.acme.com/flying_machines.html")
    cj.add_cookie_header(request2)
    response2 = mechanize.urlopen(request2)

The `CookieJar` class does all the work.  There are essentially two operations:
`.extract_cookies()` extracts HTTP cookies from `Set-Cookie` (the original
`Netscape cookie standard`) and `Set-Cookie2` (:RFC:`2965`) headers from a
response if and only if they should be set given the request, and
`.add_cookie_header()` adds `Cookie` headers if and only if they are
appropriate for a particular HTTP request.  Incoming cookies are checked for
acceptability based on the host name, etc.  Cookies are only set on outgoing
requests if they match the request's host name, path, etc.

.. _`Netscape cookie standard`: http://www.netscape.com/newsref/std/cookie_spec.html

.. note::

    If you're using `mechanize.urlopen()` (or if you're using
    `mechanize.HTTPCookieProcessor` by some other means), you don't need to
    call `.extract_cookies()` or `.add_cookie_header()` yourself*.  If, on the
    other hand, you don't want to use `urllib2`, you will need to use this pair
    of methods.  You can make your own `request` and `response` objects, which
    must support the interfaces described in the docstrings of
    `.extract_cookies()` and `.add_cookie_header()`.

There are also some `CookieJar` subclasses which can store cookies in files and
databases.  `FileCookieJar` is the abstract class for `CookieJar`s that can
store cookies in disk files.  `LWPCookieJar` saves cookies in a format
compatible with the libwww-perl library.  This class is convenient if you want
to store cookies in a human-readable file:

.. code-block:: python

    import mechanize
    cj = mechanize.LWPCookieJar()
    cj.revert("cookie3.txt")
    opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cj))
    r = opener.open("http://foobar.com/")
    cj.save("cookie3.txt")

The `.revert()` method discards all existing cookies held by the `CookieJar`
(it won't lose any existing cookies if the load fails).  The `.load()` method,
on the other hand, adds the loaded cookies to existing cookies held in the
`CookieJar` (old cookies are kept unless overwritten by newly loaded ones).

`MozillaCookieJar` can load and save to the Mozilla/Netscape/lynx-compatible
`'cookies.txt'` format.  This format loses some information (unusual and
nonstandard cookie attributes such as comment, and also information specific to
RFC 2965 cookies).  The subclass `MSIECookieJar` can load (but not save, yet)
from Microsoft Internet Explorer's cookie files (on Windows).  `BSDDBCookieJar`
(NOT FULLY TESTED!) saves to a BSDDB database using the standard library's
`bsddb` module.  There's an unfinished `MSIEDBCookieJar`, which uses (reads and
writes) the Windows MSIE cookie database directly, rather than storing copies
of cookies as `MSIECookieJar` does.

Important note
--------------

Only use names you can import directly from the `mechanize` package, and that
don't start with a single underscore.  Everything else is subject to change or
disappearance without notice.

Cooperating with Mozilla/Netscape, lynx and Internet Explorer
-------------------------------------------------------------

The subclass `MozillaCookieJar` differs from `CookieJar` only in storing
cookies using a different, Mozilla/Netscape-compatible, file format.  The lynx
browser also uses this format.  This file format can't store RFC 2965 cookies,
so they are downgraded to Netscape cookies on saving.  `LWPCookieJar` itself
uses a libwww-perl specific format ("Set-Cookie3") |--| see the example above.
Python and your browser should be able to share a cookies file (note that the
file location here will differ on non-unix OSes):

.. warning::

   You may want to backup your browser's cookies file if you use
   `MozillaCookieJar` to save cookies.  I *think* it works, but there have been
   bugs in the past!

.. code-block:: python

    import os, mechanize
    cookies = mechanize.MozillaCookieJar()
    cookies.load(os.path.join(os.environ["HOME"], "/.netscape/cookies.txt"))
    # see also the save and revert methods

Note that cookies saved while Mozilla is running will get clobbered by Mozilla
- see `MozillaCookieJar.__doc__`.

`MSIECookieJar` does the same for Microsoft Internet Explorer (MSIE) 5.x and
6.x on Windows, but does not allow saving cookies in this format.  In future,
the Windows API calls might be used to load and save (though the index has to
be read directly, since there is no API for that, AFAIK; there's also an
unfinished `MSIEDBCookieJar`, which uses (reads and writes) the Windows MSIE
cookie database directly, rather than storing copies of cookies as
`MSIECookieJar` does).

.. code-block:: python

    import mechanize
    cj = mechanize.MSIECookieJar(delayload=True)
    cj.load_from_registry()  # finds cookie index file from registry

A true `delayload` argument speeds things up.

On Windows 9x (win 95, win 98, win ME), you need to supply a username to the
`.load_from_registry()` method:

.. code-block:: python

    cj.load_from_registry(username="jbloggs")

Konqueror/Safari and Opera use different file formats, which aren't yet
supported.


Saving cookies in a file
------------------------

If you have no need to co-operate with a browser, the most convenient way to
save cookies on disk between sessions in human-readable form is to use
`LWPCookieJar`.  This class uses a libwww-perl specific format (`Set-Cookie3').
Unlike `MozilliaCookieJar`, this file format doesn't lose information.


Using your own CookieJar instance
---------------------------------

You might want to do this to `use your browser's cookies`_, to customize
`CookieJar`'s behaviour by passing constructor arguments, or to be able to get
at the cookies it will hold (for example, for saving cookies between sessions
and for debugging).

.. _`use your browser's cookies`: ./doc.html#browsers

If you're using the higher-level `urllib2`-like interface (`urlopen()`, etc),
you'll have to let it know what `CookieJar` it should use:

.. code-block:: python

    import mechanize
    cookies = mechanize.CookieJar()
    # build_opener() adds standard handlers (such as HTTPHandler and
    # HTTPCookieProcessor) by default.  The cookie processor we supply
    # will replace the default one.
    opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cookies))

    r = opener.open("http://acme.com/")  # GET
    r = opener.open("http://acme.com/", data)  # POST

The `urlopen()` function uses a global `OpenerDirector` instance to do its
work, so if you want to use `urlopen()` with your own `CookieJar`, install the
`OpenerDirector` you built with `build_opener()` using the
`mechanize.install_opener()` function, then proceed as usual:

.. code-block:: python

    mechanize.install_opener(opener)
    r = mechanize.urlopen("http://www.acme.com/")

Of course, everyone using `urlopen` is using the same global
`CookieJar` instance!

Policy
~~~~~~

You can set a policy object (must satisfy the interface defined by
`mechanize.CookiePolicy`), which determines which cookies are allowed to be set
and returned.  Use the policy argument to the `CookieJar` constructor, or use
the .set_policy() method.  The default implementation has some useful switches:

.. code-block:: python

    from mechanize import CookieJar, DefaultCookiePolicy as Policy
    cookies = CookieJar()
    # turn on RFC 2965 cookies, be more strict about domains when setting and
    # returning Netscape cookies, and block some domains from setting cookies
    # or having them returned (read the DefaultCookiePolicy docstring for the
    # domain matching rules here)
    policy = Policy(rfc2965=True, strict_ns_domain=Policy.DomainStrict,
		    blocked_domains=["ads.net", ".ads.net"])
    cookies.set_policy(policy)


Optional extras: robots.txt, HTTP-EQUIV, Refresh, Referer and seekable responses
--------------------------------------------------------------------------------

These are implemented as processor classes.  Processors are an extension of
`urllib2`'s handlers (now a standard part of urllib2 in Python 2.4): you just
pass them to `build_opener()` (example code below).


  `HTTPRobotRulesProcessor`

    WWW Robots (also called wanderers or spiders) are programs that traverse
    many pages in the World Wide Web by recursively retrieving linked pages.
    This kind of program can place significant loads on web servers, so there
    is a standard_ for a `robots.txt` file by which web site operators can
    request robots to keep out of their site, or out of particular areas of it.
    This processor uses the standard Python library's `robotparser` module.  It
    raises `mechanize.RobotExclusionError` (subclass of `urllib2.HTTPError`) if
    an attempt is made to open a URL prohibited by `robots.txt`.  XXX ATM, this
    makes use of code in the `robotparser` module that uses `urllib` - this
    will likely change in future to use `urllib2`.

  `HTTPEquivProcessor`

    The `<META HTTP-EQUIV>` tag is a way of including data in HTML to be
    treated as if it were part of the HTTP headers.  mechanize can
    automatically read these tags and add the `HTTP-EQUIV` headers to the
    response object's real HTTP headers.  The HTML is left unchanged.

  `HTTPRefreshProcessor`

    The `Refresh` HTTP header is a non-standard header which is widely used.
    It requests that the user-agent follow a URL after a specified time delay.
    mechanize can treat these headers (which may have been set in `<META
    HTTP-EQUIV>` tags) as if they were 302 redirections.  Exactly when and how
    `Refresh` headers are handled is configurable using the constructor
    arguments.

  `SeekableProcessor`

    This makes mechanize's response objects `seek()` able.  Seeking is done
    lazily (ie. the response object only reads from the socket as necessary,
    rather than slurping in all the data before the response is returned to
    you).

  `HTTPRefererProcessor`

    The `Referer` HTTP header lets the server know which URL you've just
    visited.  Some servers use this header as state information, and don't like
    it if this is not present.  It's a chore to add this header by hand every
    time you make a request.  This adds it automatically.

    .. note::

        this only makes sense if you use each processor for a single chain of
        HTTP requests (so, for example, if you use a single
        HTTPRefererProcessor to fetch a series of URLs extracted from a single
        page, **this will break**).  The mechanize_ package does this properly.

.. _mechanize: ../mechanize/


.. _standard: http://www.robotstxt.org/wc/norobots.html


.. code-block:: python

    import mechanize
    cookies = mechanize.CookieJar()

    opener = mechanize.build_opener(mechanize.HTTPRefererProcessor,
				    mechanize.HTTPEquivProcessor,
				    mechanize.HTTPRefreshProcessor,
				    mechanize.SeekableProcessor)
    opener.open("http://www.rhubarb.com/")


.. _requests:

Confusing fact about headers and Requests
-----------------------------------------

mechanize automatically upgrades `urllib2.Request` objects to
`mechanize.Request`, as a backwards-compatibility hack.  This means that you
won't see any headers that are added to Request objects by handlers unless you
use `mechanize.Request` in the first place.  Sorry about that.


.. _headers:

Adding headers
--------------

Adding headers is done like so:

.. code-block:: python

    import mechanize, urllib2
    req = urllib2.Request("http://foobar.com/")
    req.add_header("Referer", "http://wwwsearch.sourceforge.net/mechanize/")
    r = mechanize.urlopen(req)

You can also use the headers argument to the `urllib2.Request` constructor.

`urllib2` (in fact, mechanize takes over this task from `urllib2`) adds some
headers to `Request` objects automatically - see the next section for details.


Changing the automatically-added headers (User-Agent)
-----------------------------------------------------

`OpenerDirector` automatically adds a `User-Agent` header to every `Request`.

To change this and/or add similar headers, use your own `OpenerDirector`:

.. code-block:: python

    import mechanize
    cookies = mechanize.CookieJar()
    opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cookies))
    opener.addheaders = [("User-agent", "Mozilla/5.0 (compatible; MyProgram/0.1)"),
			 ("From", "responsible.person@example.com")]


Again, to use `urlopen()`, install your `OpenerDirector` globally:

.. code-block:: python

    mechanize.install_opener(opener)
    r = mechanize.urlopen("http://acme.com/")


Also, a few standard headers (`Content-Length`, `Content-Type` and `Host`) are
added when the `Request` is passed to `urlopen()` (or `OpenerDirector.open()`).
mechanize explictly adds these (and `User-Agent`) to the `Request` object,
unlike versions of `urllib2` before Python 2.4 (but <strong>note</strong> that
Content-Length is an exception to this rule: it is sent, but not explicitly
added to the `Request`'s headers; this is due to a bug in `httplib` in Python
2.3 and earlier).  You shouldn't need to change these headers, but since this
is done by `AbstractHTTPHandler`, you can change the way it works by passing a
subclass of that handler to `build_opener()` (or, as always, by constructing an
opener yourself and calling .add_handler()).


.. _unverifiable:

Initiating unverifiable transactions
------------------------------------

This section is only of interest for correct handling of third-party HTTP
cookies.  See below_ for an explanation of 'third-party'.

.. _below: ./doc.html#standards

First, some terminology.

An *unverifiable request* (defined fully by RFC 2965) is one whose URL the user
did not have the option to approve.  For example, a transaction is unverifiable
if the request is for an image in an HTML document, and the user had no option
to approve the fetching of the image from a particular URL.

The *request-host of the origin transaction* (defined fully by RFC 2965) is the
host name or IP address of the original request that was initiated by the user.
For example, if the request is for an image in an HTML document, this is the
request-host of the request for the page containing the image.

.. note::

    mechanize knows that redirected transactions are unverifiable, and will
    handle that on its own (ie. you don't need to think about the origin
    request-host or verifiability yourself).

If you want to initiate an unverifiable transaction yourself (which you should
if, for example, you're downloading the images from a page, and 'the user'
hasn't explicitly OKed those URLs):

  - If you're using a `urllib2.Request` from Python 2.3 or earlier, set the
    `unverifiable` and `origin_req_host` attributes on your `Request` instance:

.. code-block:: python

    request.unverifiable = True
    request.origin_req_host = "www.example.com"

  - If you're using a `urllib2.Request` from Python 2.4 or later, or you're
    using a `mechanize.Request`, use the `unverifiable` and `origin_req_host`
    arguments to the constructor:

.. code-block:: python

    request = Request(origin_req_host="www.example.com", unverifiable=True)



.. _rfc2965:

RFC 2965 handling
-----------------

RFC 2965 handling is switched off by default, because few browsers implement
it, so the RFC 2965 protocol is essentially never seen on the internet.  To
switch it on, see here__.

__ ./doc.html#policy


.. _debugging:

Debugging
---------

.. XXX move as much as poss. to General page

First, a few common problems.  The most frequent mistake people seem to make is
to use `mechanize.urlopen()`, *and* the `.extract_cookies()` and
`.add_cookie_header()` methods on a cookie object themselves.  If you use
`mechanize.urlopen()` (or `OpenerDirector.open()`), the module handles
extraction and adding of cookies by itself, so you should not call
`.extract_cookies()` or `.add_cookie_header()`.

Are you sure the server is sending you any cookies in the first place?  Maybe
the server is keeping track of state in some other way (`HIDDEN` HTML form
entries (possibly in a separate page referenced by a frame), URL-encoded
session keys, IP address, HTTP `Referer` headers)?  Perhaps some embedded
script in the HTML is setting cookies (see below)?  Maybe you messed up your
request, and the server is sending you some standard failure page (even if the
page doesn't appear to indicate any failure).  Sometimes, a server wants
particular headers set to the values it expects, or it won't play nicely.  The
most frequent offenders here are the `Referer` [*sic*] and / or `User-Agent`
HTTP headers (`see above`__ for how to set these).  The `User-Agent` header may
need to be set to a value like that of a popular browser.  The `Referer` header
may need to be set to the URL that the server expects you to have followed a
link from.  Occasionally, it may even be that operators deliberately configure
a server to insist on precisely the headers that the popular browsers (MS
Internet Explorer, Mozilla/Netscape, Opera, Konqueror/Safari) generate, but
remember that incompetence (possibly on your part) is more probable than
deliberate sabotage (and if a site owner is that keen to stop robots, you
probably shouldn't be scraping it anyway).

__ ./doc.html#headers

When you `.save()` to or `.load()`/`.revert()` from a file, single-session
cookies will expire unless you explicitly request otherwise with the
`ignore_discard` argument.  This may be your problem if you find cookies are
going away after saving and loading.

.. code-block:: python

    import mechanize
    cj = mechanize.LWPCookieJar()
    opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cj))
    mechanize.install_opener(opener)
    r = mechanize.urlopen("http://foobar.com/")
    cj.save("/some/file", ignore_discard=True, ignore_expires=True)


If none of the advice above solves your problem quickly, try comparing the
headers and data that you are sending out with those that a browser emits.
Often this will give you the clue you need.  Of course, you'll want to check
that the browser is able to do manually what you're trying to achieve
programatically before minutely examining the headers.  Make sure that what you
do manually is *exactly* the same as what you're trying to do from Python - you
may simply be hitting a server bug that only gets revealed if you view pages in
a particular order, for example.  In order to see what your browser is sending
to the server (even if HTTPS is in use), see `the General FAQ page`_.  If
nothing is obviously wrong with the requests your program is sending and you're
out of ideas, you can try the last resort of good old brute force binary-search
debugging.  Temporarily switch to sending HTTP headers (with `httplib`).  Start
by copying Netscape/Mozilla or IE slavishly (apart from session IDs, etc., of
course), then begin the tedious process of mutating your headers and data until
they match what your higher-level code was sending.  This will at least
reliably find your problem.

.. _`the General FAQ page`: ../GeneralFAQ.html

You can turn on display of HTTP headers:

.. code-block:: python

    import mechanize
    hh = mechanize.HTTPHandler()  # you might want HTTPSHandler, too
    hh.set_http_debuglevel(1)
    opener = mechanize.build_opener(hh)
    response = opener.open(url)

Alternatively, you can examine your individual request and response objects to
see what's going on.  Note, though, that mechanize upgrades urllib2.Request
objects to mechanize.Request, so you won't see any headers that are added to
requests by handlers unless you use mechanize.Request in the first place.
mechanize's responses can be made `.seek()`able using `SeekableProcessor`.
It's often useful to use the `.seek()` method like this during debugging:

.. code-block:: python

    ...
    response = mechanize.urlopen("http://spam.eggs.org/")
    print response.read()
    response.seek(0)
    # rest of code continues as if you'd never .read() the response
    ...


Also, note `HTTPRedirectDebugProcessor` (which prints information about
redirections) and `HTTPResponseDebugProcessor` (which prints out all response
bodies, including those that are read during redirections).

.. note::

    As well as having these processors in your `OpenerDirector` (for example,
    by passing them to `build_opener()`) you have to turn on logging at the
    `INFO` level or lower in order to see any output.

If you would like to see what is going on in mechanize's tiny mind, do this:

.. code-block:: python

    import sys, logging
    # logging.DEBUG covers masses of debugging information,
    # logging.INFO just shows the output from HTTPRedirectDebugProcessor,
    logger = logging.getLogger("mechanize")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)

The `DEBUG` level (as opposed to the `INFO` level) can actually be quite
useful, as it explains why particular cookies are accepted or rejected and why
they are or are not returned.

One final thing to note is that there are some catch-all bare `except:`
statements in the module, which are there to handle unexpected bad input
without crashing your program.  If this happens, it's a bug in mechanize, so
please mail me the warning text.


.. _script:

Embedded script that sets cookies
---------------------------------

It is possible to embed script in HTML pages (sandwiched between
`<SCRIPT>here</SCRIPT>` tags, and in `javascript:` URLs) - JavaScript /
ECMAScript, VBScript, or even Python - that causes cookies to be set in a
browser.  See the `General FAQs`_ page for what to do about this.

.. _`General FAQs`: ../bits/GeneralFAQ.html


.. _dates:

Parsing HTTP date strings
-------------------------

A function named `str2time` is provided by the package, which may be useful for
parsing dates in HTTP headers.  `str2time` is intended to be liberal, since
HTTP date/time formats are poorly standardised in practice.  There is no need
to use this function in normal operations: `CookieJar` instances keep track of
cookie lifetimes automatically.  This function will stay around in some form,
though the supported date/time formats may change.


.. _badhtml:

Dealing with bad HTML
---------------------

XXX Intro

XXX Test me

.. code-block:: python

    import copy
    import mechanize
    class CommentCleanProcessor(mechanize.BaseProcessor):
	  def http_response(self, request, response):
	      if not hasattr(response, "seek"):
		  response = mechanize.response_seek_wrapper(response)
	      response.seek(0)
	      new_response = copy.copy(response)
	      new_response.set_data(
		  re.sub("<!-([^-]*)->", "<!--\\1-->", response.read()))
	      return new_response
	  https_response = http_response


XXX TidyProcessor: mxTidy?  tidylib?  tidy?


.. _standards:

Note about cookie standards
---------------------------

The various cookie standards and their history form a case study of the
terrible things that can happen to a protocol.  The long-suffering David
Kristol has written a paper_ about it, if you want to know the gory details.

.. _paper: http://arxiv.org/abs/cs.SE/0105018

Here is a summary.

The `Netscape protocol`_ (cookie_spec.html) is still the only standard
supported by most browsers (including Internet Explorer and Netscape).  Be
aware that cookie_spec.html is not, and never was, actually followed to the
letter (or anything close) by anyone (including Netscape, IE and mechanize):
the Netscape protocol standard is really defined by the behaviour of Netscape
(and now IE).  Netscape cookies are also known as V0 cookies, to distinguish
them from RFC 2109 or RFC 2965 cookies, which have a version cookie-attribute
with a value of 1.

.. _`Netscape protocol`: http://www.netscape.com/newsref/std/cookie_spec.html

:RFC:`2109` was introduced to fix some problems identified with the Netscape
protocol, while still keeping the same HTTP headers (`Cookie` and
`Set-Cookie`).  The most prominent of these problems is the 'third-party'
cookie issue, which was an accidental feature of the Netscape protocol.  When
one visits www.bland.org, one doesn't expect to get a cookie from
www.lurid.com, a site one has never visited.  Depending on browser
configuration, this can still happen, because the unreconstructed Netscape
protocol is happy to accept cookies from, say, an image in a webpage
(www.bland.org) that's included by linking to an advertiser's server
(www.lurid.com).  This kind of event, where your browser talks to a server that
you haven't explicitly okayed by some means, is what the RFCs call an
'unverifiable transaction'.  In addition to the potential for embarrassment
caused by the presence of lurid.com's cookies on one's machine, this may also
be used to track your movements on the web, because advertising agencies like
doubleclick.net place ads on many sites.  RFC 2109 tried to change this by
requiring cookies to be turned off during unverifiable transactions with
third-party servers - unless the user explicitly asks them to be turned on.
This clashed with the business model of advertisers like doubleclick.net, who
had started to take advantage of the third-party cookies 'bug'.  Since the
browser vendors were more interested in the advertisers' concerns than those of
the browser users, this arguably doomed both RFC 2109 and its successor, RFC
2965, from the start.  Other problems than the third-party cookie issue were
also fixed by 2109.  However, even ignoring the advertising issue, 2109 was
stillborn, because Internet Explorer and Netscape behaved differently in
response to its extended `Set-Cookie` headers.  This was not really RFC 2109's
fault: it worked the way it did to keep compatibility with the Netscape
protocol as implemented by Netscape.  Microsoft Internet Explorer (MSIE) was
very new when the standard was designed, but was starting to be very popular
when the standard was finalised.  XXX P3P, and MSIE & Mozilla options

XXX Apparently MSIE implements bits of RFC 2109 - but not very compliant
(surprise).  Presumably other browsers do too, as a result.  mechanize already
does allow Netscape cookies to have `max-age` and `port` cookie-attributes, and
as far as I know that's the extent of the support present in MSIE.  I haven't
tested, though!

:RFC:`2965` attempted to fix the compatibility problem by introducing two new
headers, `Set-Cookie2` and `Cookie2`.  Unlike the `Cookie` header, `Cookie2`
does *not* carry cookies to the server - rather, it simply advertises to the
server that RFC 2965 is understood.  `Set-Cookie2` *does* carry cookies, from
server to client: the new header means that both IE and Netscape completely
ignore these cookies.  This prevents breakage, but introduces a chicken-egg
problem that means 2965 may never be widely adopted, especially since Microsoft
shows no interest in it.  XXX Rumour has it that the European Union is unhappy
with P3P, and might introduce legislation that requires something better,
forming a gap that RFC 2965 might fill - any truth in this?  Opera is the only
browser I know of that supports the standard.  On the server side, Apache's
`mod_usertrack` supports it.  One confusing point to note about RFC 2965 is
that it uses the same value (1) of the Version attribute in HTTP headers as
does RFC 2109.

Most recently, it was discovered that RFC 2965 does not fully take account of
issues arising when 2965 and Netscape cookies coexist, and errata were
discussed on the W3C http-state mailing list, but the list traffic died and it
seems RFC 2965 is dead as an internet protocol (but still a useful basis for
implementing the de-facto standards, and perhaps as an intranet protocol).

Because Netscape cookies are so poorly specified, the general philosophy of the
module's Netscape cookie implementation is to start with RFC 2965 and open
holes where required for Netscape protocol-compatibility.  RFC 2965 cookies are
*always* treated as RFC 2965 requires, of course!


.. _faq_pre:

FAQs - pre install
------------------

  - Doesn't the standard Python library module, `Cookie`, do this?

    No: Cookie.py does the server end of the job.  It doesn't know when to
    accept cookies from a server or when to pass them back.

  - Is urllib2.py required?

    No.  You probably want it, though.

  - Where can I find out more about the HTTP cookie protocol?

    There is more than one protocol, in fact (see the docs_ for a brief
    explanation of the history):

    - The original `Netscape cookie protocol`_ - the standard still in use
      today, in theory (in reality, the protocol implemented by all the major
      browsers only bears a passing resemblance to the protocol sketched out in
      this document).

.. _`Netscape cookie protocol`: http://www.netscape.com/newsref/std/cookie_spec.html

    - :RFC:`2109` - obsoleted by RFC 2965.

    - :RFC:`2965` - the Netscape protocol with the bugs fixed (not widely used
      |--| the Netscape protocol still dominates, and seems likely to remain
      dominant indefinitely, at least on the Internet).  :RFC:`2964` discusses
      use of the protocol.  Errata_ to RFC 2965 are currently being discussed on
      the `http-state mailing list`_ (update: list traffic died months ago and
      hasn't revived).

.. _`http-state mailing list`: http://lists.bell-labs.com/mailman/listinfo/http-state

.. _Errata: http://kristol.org/cookie/errata.html

    - A paper_ by David Kristol setting out the history of the cookie standards
      in exhausting detail.

    - HTTP cookies FAQ.

.. _FAQ: http://www.cookiecentral.com

  - Which protocols does ClientCookie support?

    Netscape and RFC 2965.  RFC 2965 handling is switched off by default.

  - What about RFC 2109?

    RFC 2109 cookies are currently parsed as Netscape cookies, and treated by
    default as RFC 2965 cookies thereafter if RFC 2965 handling is enabled, or
    as Netscape cookies otherwise.  RFC 2109 is officially obsoleted by RFC
    2965.  Browsers do use a few RFC 2109 features in their Netscape cookie
    implementations (`port` and `max-age`), and ClientCookie knows about that,
    too.

.. _docs: ./doc.html


.. _faq_use:

FAQs - usage
------------

  - Why don't I have any cookies?

    Read the `debugging section`_ of this page.

.. _`debugging section`: ./doc.html#debugging

  - My response claims to be empty, but I know it's not!

    Did you call `response.read()` (eg., in a debug statement), then forget
    that all the data has already been read?  In that case, you may want to use
    `SeekableProcessor`.

  - How do I download only part of a response body?

    Just call `.read()` or `.readline()` methods on your response object as
    many times as you need.  The `.seek()` method (which will only be there if
    you're using `SeekableProcessor`) still works, because
    `SeekableProcessor`'s response objects cache read data.

  - What's the difference between the `.load()` and

    `.revert()` methods of `CookieJar`?  `.load()` <emph>appends</emph> cookies
    from a file.  `.revert()` discards all existing cookies held by the
    `CookieJar` first (but it won't lose any existing cookies if the loading
    fails).

  - Is it threadsafe?

    No.  *Tested* patches welcome.  Clarification: As far as I know,
    it's perfectly possible to use mechanize in threaded code, but it provides
    no synchronisation: you have to provide that yourself.  <li>How do I do
    <X> The module docstrings are worth reading if you want to do
    something unusual.

  - What's this "processor" business about?  I knew `urllib2` used "handlers",
    but not these "processors".

    This Python library patch_ contains an explanation.  Processors are now a
    standard part of urllib2 in Python 2.4.

.. _patch: http://www.python.org/sf/852995

  - How do I use it without urllib2.py?

.. code-block:: python

    from mechanize import CookieJar
    print CookieJar.extract_cookies.__doc__
    print CookieJar.add_cookie_header.__doc__


I prefer questions and comments to be sent to the `mailing list` rather than
direct to me.

.. _`mailing list`: http://lists.sourceforge.net/lists/listinfo/wwwsearch-general


.. |--| unicode:: U+2013
