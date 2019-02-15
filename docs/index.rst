mechanize
=====================================

Stateful programmatic web browsing in Python. Browse pages programmatically
with easy HTML form filling and clicking of links.

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents:

   faq
   browser_api
   forms_api
   advanced


Quickstart
------------

The examples below are written for a website that does not exist
(`example.com`), so cannot be run.

.. code-block:: python

    import re
    import mechanize

    br = mechanize.Browser()
    br.open("http://www.example.com/")
    # follow second link with element text matching regular expression
    response1 = br.follow_link(text_regex=r"cheese\s*shop", nr=1)
    print(br.title())
    print(response1.geturl())
    print(response1.info())  # headers
    print(response1.read())  # body

    br.select_form(name="order")
    # Browser passes through unknown attributes (including methods)
    # to the selected HTMLForm.
    br["cheeses"] = ["mozzarella", "caerphilly"]  # (the method here is __setitem__)
    # Submit current form.  Browser calls .close() on the current response on
    # navigation, so this closes response1
    response2 = br.submit()

    # print currently selected form (don't call .submit() on this, use br.submit())
    print(br.form)

    response3 = br.back()  # back to cheese shop (same data as response1)
    # the history mechanism returns cached response objects
    # we can still use the response, even though it was .close()d
    response3.get_data()  # like .seek(0) followed by .read()
    response4 = br.reload()  # fetches from server

    for form in br.forms():
        print(form)
    # .links() optionally accepts the keyword args of .follow_/.find_link()
    for link in br.links(url_regex="python.org"):
        print(link)
        br.follow_link(link)  # takes EITHER Link instance OR keyword args
        br.back()


You may control the browser's policy by using the methods of
`mechanize.Browser`'s base class, `mechanize.UserAgent`.  For example:

.. code-block:: python

    br = mechanize.Browser()
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
    # Add an extra header to all outgoing requests, you can also
    # re-order or remove headers in this function.
    br.finalize_request_headers = lambda request, headers: headers.__setitem__(
      'My-Custom-Header', 'Something')
    # Don't handle HTTP-EQUIV headers (HTTP headers embedded in HTML).
    br.set_handle_equiv(False)
    # Ignore robots.txt.  Do not do this without thought and consideration.
    br.set_handle_robots(False)
    # Don't add Referer (sic) header
    br.set_handle_referer(False)
    # Don't handle Refresh redirections
    br.set_handle_refresh(False)
    # Don't handle cookies
    br.set_cookiejar()
    # Supply your own mechanize.CookieJar (NOTE: cookie handling is ON by
    # default: no need to do this unless you have some reason to use a
    # particular cookiejar)
    br.set_cookiejar(cj)
    # Tell the browser to send the Accept-Encoding: gzip header to the server
    # to indicate it supports gzip Content-Encoding
    br.set_request_gzip(True)
    # Do not verify SSL certificates
    import ssl
    br.set_ca_data(context=ssl._create_unverified_context(cert_reqs=ssl.CERT_NONE)
    # Log information about HTTP redirects and Refreshes.
    br.set_debug_redirects(True)
    # Log HTTP response bodies (i.e. the HTML, most of the time).
    br.set_debug_responses(True)
    # Print HTTP headers.
    br.set_debug_http(True)

    # To make sure you're seeing all debug output:
    logger = logging.getLogger("mechanize")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

    # Sometimes it's useful to process bad headers or bad HTML:
    response = br.response()  # this is a copy of response
    headers = response.info()  # this is a HTTPMessage
    headers["Content-type"] = "text/html; charset=utf-8"
    response.set_data(response.get_data().replace("<!---", "<!--"))
    br.set_response(response)

mechanize exports the complete interface of `urllib2`:

.. code-block:: python

    import mechanize
    response = mechanize.urlopen("http://www.example.com/")
    print(response.read())

When using mechanize, anything you would normally import from `urllib2` should
be imported from mechanize instead.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
