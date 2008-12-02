#!/usr/bin/env python
"""
%prog port

e.g. %prog 8000

Runs a local server to point the mechanize functional tests at.  Example:

python test-tools/twisted-localserver.py 8042
python functional_tests.py --uri=http://localhost:8042/

You need twisted.web2 to run it.  On ubuntu feisty, you can install it like so:

sudo apt-get install python-twisted-web2
"""

import sys, re

from twisted.cred import portal, checkers
from twisted.internet import reactor
from twisted.web2 import server, http, resource, channel, \
     http_headers, responsecode, twcgi
from twisted.web2.auth import basic, digest, wrapper
from twisted.web2.auth.interfaces import IHTTPUser

from zope.interface import implements


def html(title=None):
    f = open("README.html", "r")
    html = f.read()
    if title is not None:
        html = re.sub("<title>(.*)</title>", "<title>%s</title>" % title, html)
    return html

MECHANIZE_HTML = html()
ROOT_HTML = html("Python bits")
RELOAD_TEST_HTML = """\
<html>
<head><title>Title</title></head>
<body>

<a href="/mechanize">near the start</a>

<p>Now some data to prevent HEAD parsing from reading the link near
the end.

<pre>
%s</pre>

<a href="/mechanize">near the end</a>

</body>

</html>""" % (("0123456789ABCDEF"*4+"\n")*61)
REFERER_TEST_HTML = """\
<html>
<head>
<title>mechanize Referer (sic) test page</title>
</head>
<body>
<p>This page exists to test the Referer functionality of <a href="/mechanize">mechanize</a>.
<p><a href="/cgi-bin/cookietest.cgi">Here</a> is a link to a page that displays the Referer header.
</body>
</html>"""


BASIC_AUTH_PAGE = """
<html>
<head>
<title>Basic Auth Protected Area</title>
</head>
<body>
<p>Hello, basic auth world.
<p>
</body>
</html>
"""


DIGEST_AUTH_PAGE = """
<html>
<head>
<title>Digest Auth Protected Area</title>
</head>
<body>
<p>Hello, digest auth world.
<p>
</body>
</html>
"""


class TestHTTPUser(object):
    """
    Test avatar implementation for http auth with cred
    """
    implements(IHTTPUser)

    username = None

    def __init__(self, username):
        """
        @param username: The str username sent as part of the HTTP auth
            response.
        """
        self.username = username


class TestAuthRealm(object):
    """
    Test realm that supports the IHTTPUser interface
    """

    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IHTTPUser in interfaces:
            if avatarId == checkers.ANONYMOUS:
                return IHTTPUser, TestHTTPUser('anonymous')

            return IHTTPUser, TestHTTPUser(avatarId)

        raise NotImplementedError("Only IHTTPUser interface is supported")


class Page(resource.Resource):

  addSlash = True
  content_type = http_headers.MimeType("text", "html")

  def render(self, ctx):
    return http.Response(
        responsecode.OK,
        {"content-type": self.content_type},
        self.text)

def _make_page(parent, name, text, content_type, wrapper,
               leaf=False):
    page = Page()
    page.text = text
    base_type, specific_type = content_type.split("/")
    page.content_type = http_headers.MimeType(base_type, specific_type)
    page.addSlash = not leaf
    parent.putChild(name, wrapper(page))
    return page

def make_page(parent, name, text,
              content_type="text/html", wrapper=lambda page: page):
    return _make_page(parent, name, text, content_type, wrapper, leaf=False)

def make_leaf_page(parent, name, text,
                   content_type="text/html", wrapper=lambda page: page):
    return _make_page(parent, name, text, content_type, wrapper, leaf=True)

def make_redirect(parent, name, location_relative_ref):
    redirect = resource.RedirectResource(path=location_relative_ref)
    setattr(parent, "child_"+name, redirect)
    return redirect

def make_cgi_bin(parent, name, dir_name):
    cgi_bin = twcgi.CGIDirectory(dir_name)
    setattr(parent, "child_"+name, cgi_bin)
    return cgi_bin

def require_basic_auth(resource):
    p = portal.Portal(TestAuthRealm())
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse()
    c.addUser("john", "john")
    p.registerChecker(c)
    cred_factory = basic.BasicCredentialFactory("Basic Auth protected area")
    return wrapper.HTTPAuthResource(resource,
                                    [cred_factory],
                                    p,
                                    interfaces=(IHTTPUser,))

def require_digest_auth(resource):
    p = portal.Portal(TestAuthRealm())
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse()
    c.addUser("digestuser", "digestuser")
    p.registerChecker(c)
    cred_factory = digest.DigestCredentialFactory("MD5",
                                                  "Digest Auth protected area")
    return wrapper.HTTPAuthResource(resource,
                                    [cred_factory],
                                    p,
                                    interfaces=(IHTTPUser,))

def main():
    root = Page()
    root.text = ROOT_HTML
    make_page(root, "mechanize", MECHANIZE_HTML)
    make_leaf_page(root, "robots.txt",
                   "User-Agent: *\nDisallow: /norobots",
                   "text/plain")
    make_leaf_page(root, "robots", "Hello, robots.", "text/plain")
    make_leaf_page(root, "norobots", "Hello, non-robots.", "text/plain")
    bits = make_page(root, "bits", "GeneralFAQ.html")
    make_leaf_page(bits, "cctest2.txt",
                   "Hello ClientCookie functional test suite.",
                   "text/plain")
    make_leaf_page(bits, "referertest.html", REFERER_TEST_HTML)
    make_leaf_page(bits, "mechanize_reload_test.html", RELOAD_TEST_HTML)
    make_redirect(root, "redirected", "/doesnotexist")
    make_cgi_bin(root, "cgi-bin", "test-tools")
    make_page(root, "basic_auth", BASIC_AUTH_PAGE, wrapper=require_basic_auth)
    make_page(root, "digest_auth", DIGEST_AUTH_PAGE,
              wrapper=require_digest_auth)

    site = server.Site(root)
    reactor.listenTCP(int(sys.argv[1]), channel.HTTPFactory(site))
    reactor.run()

main()
