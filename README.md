mechanize - Automate interaction with HTTP web servers
==========================================================

[![Build Status](https://api.travis-ci.org/python-mechanize/mechanize.svg)](https://travis-ci.org/python-mechanize/mechanize)
[![Build status](https://ci.appveyor.com/api/projects/status/github/kovidgoyal/mechanize?svg=true)](https://ci.appveyor.com/project/kovidgoyal/mechanize)

Major features
-----------------

Stateful programmatic web browsing in Python, after Andy Lester's Perl
module [`WWW::Mechanize`](http://search.cpan.org/dist/WWW-Mechanize/).

  * `mechanize.Browser` and `mechanize.UserAgentBase` implement the
    interface of `urllib2.OpenerDirector`, so:

      * any URL can be opened, not just `http:`

      * `mechanize.UserAgentBase` offers easy dynamic configuration of
        user-agent features like protocol, cookie, redirection and
        `robots.txt` handling, without having to make a new
        `OpenerDirector` each time, e.g. by calling `build_opener()`.

  * Easy HTML form filling.

  * Convenient link parsing and following.

  * Browser history (`.back()` and `.reload()` methods).

  * The `Referer` HTTP header is added properly (optional).

  * Automatic observance of
    [`robots.txt`](http://www.robotstxt.org/wc/norobots.html).

  * Automatic handling of HTTP-Equiv and Refresh.


Installation
-----------------

To install for normal usage:
```
sudo pip2 install mechanize
```

To install for development:
```
git clone https://github.com/python-mechanize/mechanize.git
cd mechanize
sudo pip2 install -e
```

To install manually, simply add the `mechanize` sub-directory somwhere on your
`PYTHONPATH`.

Examples
----------

The examples below are written for a website that does not exist
(`example.com`), so cannot be run.  

```python
import re
import mechanize

br = mechanize.Browser()
br.open("http://www.example.com/")
# follow second link with element text matching regular expression
response1 = br.follow_link(text_regex=r"cheese\s*shop", nr=1)
assert br.viewing_html()
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
```

You may control the browser's policy by using the methods of
`mechanize.Browser`'s base class, `mechanize.UserAgent`.  For example:

```python
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
headers["Content-type"] = "text/html; charset=utf-8"
response.set_data(response.get_data().replace("<!---", "<!--"))
br.set_response(response)
```

mechanize exports the complete interface of `urllib2`:

```python
import mechanize
response = mechanize.urlopen("http://www.example.com/")
print response.read()
```

When using mechanize, anything you would normally import from `urllib2` should
be imported from mechanize instead.

Thread safety
---------------

The global `mechanize.urlopen()` and `mechanize.urlretrieve()` functions are
thread safe. However, mechanize browser instances **are not** thread safe. If
you want to use a mechanize Browser instance in multiple threads, clone it,
using `copy.copy(browser_object)` method. The clone will share the same,
thread safe cookie jar, and have the same settings/handlers as the original,
but all other state is not shared, making the clone safe to use in a different
thread.

Using custom CA certificates
-------------------------------

mechanize supports the same mechanism for using custom CA certificates as
python >= 2.7.9. To change the certificates a mechanize browser instance uses,
call the `set_ca_data()` method on it. This method accepts the same arguments
as the
[`SSLContext.load_verify_locations()`](https://docs.python.org/2/library/ssl.html#ssl.SSLContext.load_verify_locations)
method from the python standard library. You can also pass a pre-built context
via the `context` keyword argument. Note that to use this feature, you
must be using python >= 2.7.9.


Credits
-----------------

python-mechanize was the creation of John J. Lee. Maintenance was taken over by
Kovid Goyal in 2017.

Much of the code was originally derived from the work of the following people:

 * Gisle Aas -- [libwww-perl](http://search.cpan.org/dist/libwww-perl/)

 * Jeremy Hylton (and many others) --
[urllib2](http://docs.python.org/release/2.6/library/urllib2.html)

 * Andy Lester -- [WWW::Mechanize](http://search.cpan.org/dist/WWW-Mechanize/)

 * Johnny Lee (coincidentally-named) -- MSIE CookieJar Perl code from which
mechanize's support for that is derived.

Also:

 * Gary Poster and Benji York at Zope Corporation -- contributed significant
changes to the HTML forms code

 * Ronald Tschalar -- provided help with Netscape cookies

Thanks also to the many people who have contributed bug reports and
patches.
