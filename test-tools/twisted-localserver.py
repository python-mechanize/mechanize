#!/usr/bin/env python
"""
%prog port

e.g. %prog 8000

Runs a local server to point the mechanize functional tests at.  Example:

python test-tools/twisted-localserver.py 8042
python functional_tests.py --uri=http://localhost:8042/

You need twisted.web to run it.
"""

import optparse
import os
import re
import sys
import time

from twisted.cred import checkers, portal
from twisted.internet import reactor
from twisted.python import log
from twisted.web import http, resource, server
from twisted.web.guard import (BasicCredentialFactory, DigestCredentialFactory,
                               HTTPAuthSessionWrapper)
from twisted.web.resource import IResource, EncodingResourceWrapper
from twisted.web.server import GzipEncoderFactory
from twisted.web.util import Redirect
from zope.interface import implementer


def gzip_wrapper(page):
    return EncodingResourceWrapper(page, [GzipEncoderFactory()])


def html(title=None, extra_content=""):
    html = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
    <title>mechanize</title>
  </head>
  <body><a href="http://sourceforge.net/">
%s
</body>
</html>
""" % extra_content
    if title is not None:
        html = re.sub("<title>(.*)</title>", "<title>%s</title>" % title, html)
    return html


MECHANIZE_HTML = html()
ROOT_HTML = html("mechanize")
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

</html>""" % (("0123456789ABCDEF" * 4 + "\n") * 61)
REFERER_TEST_HTML = """\
<html>
<head>
<title>mechanize Referer (sic) test page</title>
</head>
<body>
<p>This page exists to test the Referer functionality of \
<a href="/mechanize">mechanize</a>.
<p><a href="/dynamic">Here</a>\
is a link to a page that displays the Referer header.
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
    isLeaf = True

    def render(self, request):
        return self.template.encode('utf-8')

    def __init__(self, template, username):
        self.template = template
        self.username = username


@implementer(portal.IRealm)
class TestAuthRealm(object):
    """
    Test realm that supports the IHTTPUser interface
    """

    def __init__(self, template=BASIC_AUTH_PAGE):
        self.template = template

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            if avatarId == checkers.ANONYMOUS:
                return (IResource, TestHTTPUser(self.template, 'anonymous'),
                        lambda: None)

            return (IResource, TestHTTPUser(self.template, avatarId),
                    lambda: None)

        raise NotImplementedError("Only IResource interface is supported")


class Page(resource.Resource):

    def __init__(self, text='', leaf=False, content_type='text/html'):
        self.isLeaf = leaf
        self.content_type = content_type
        self.text = text
        resource.Resource.__init__(self)

    def getChild(self, path, request):
        if not path:
            return self
        return resource.Resource.getChild(self, path, request)

    def render(self, request):
        request.setResponseCode(http.OK)
        request.setHeader('content-type', self.content_type)
        return self.text.encode('utf-8')


class DynamicPage(resource.Resource):

    isLeaf = True

    def getChild(self, path, request):
        if not path:
            return self
        return resource.Resource.getChild(self, path, request)

    def render(self, request):
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/html')
        year_plus_one = time.localtime(time.time())[0] + 1
        expires = "09-Nov-%d 23:12:40 GMT" % (year_plus_one,)
        request.addCookie('foo', 'bar', expires=expires)
        request.addCookie('sessioncookie', 'spam\n')
        html = (
            "<html><head><title>Cookies/form submission parameters</title>")
        if request.args.get(b'refresh'):
            html += '<meta http-equiv="refresh" content=\'%s\'>' % (
                request.args.get(b'refresh')[0].decode('ascii'))
        elif not request.getCookie(b'foo'):
            html += '<meta http-equiv="refresh" content="1">'
        html += "</head><body>"
        if request.getHeader(b'referer'):
            html += "<p>Referer:</p><pre>{}</pre>".format(
                    request.getHeader(b'referer'))
        html += "<p>Received cookies:</p>"
        html += "<pre>"
        html += request.getHeader('cookie') or ''
        html += "</pre>"
        if request.getCookie(b'foo'):
            html += "<p>Your browser supports cookies!"
        if request.getCookie(b'sessioncookie'):
            html += "<p>Received session cookie"

        html += '</body></html>'
        return html.encode('utf-8')


def _make_page(parent, name, text, content_type, wrapper,
               leaf=False):
    page = Page(text=text, leaf=leaf, content_type=content_type)
    name = name.encode('utf-8')
    parent.putChild(name, wrapper(page))
    return page


def make_page(parent, name, text,
              content_type="text/html", wrapper=lambda page: page):
    return _make_page(parent, name, text, content_type, wrapper, leaf=False)


def make_leaf_page(parent, name, text,
                   content_type="text/html", wrapper=lambda page: page):
    return _make_page(parent, name, text, content_type, wrapper, leaf=True)


def make_redirect(parent, name, location_relative_ref):
    redirect = Redirect(location_relative_ref)
    name = name.encode('utf-8')
    parent.putChild(name, redirect)
    return redirect


def require_basic_auth(resource):
    p = portal.Portal(TestAuthRealm())
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse(john=b'john')
    p.registerChecker(c)
    cred_factory = BasicCredentialFactory("Basic Auth protected area")
    return HTTPAuthSessionWrapper(p, [cred_factory])


def require_digest_auth(resource):
    p = portal.Portal(TestAuthRealm(DIGEST_AUTH_PAGE))
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse(
            digestuser=b'digestuser')
    p.registerChecker(c)
    cred_factory = DigestCredentialFactory(
            "md5", b"Digest Auth protected area")
    return HTTPAuthSessionWrapper(p, [cred_factory])


def parse_options(args):
    parser = optparse.OptionParser()
    parser.add_option("--log", action="store_true")
    options, remaining_args = parser.parse_args(args)
    options.port = int(remaining_args[0]) if remaining_args else 8000
    return options


def main(argv):
    options = parse_options(argv[1:])
    if options.log:
        log.startLogging(sys.stdout)

    # This is supposed to match the SF site so it's easy to run a functional
    # test over the internet and against Apache.
    # TODO: Remove bizarre structure and strings expected by functional tests.
    root = Page(text=ROOT_HTML)
    mechanize = make_page(root, "mechanize", MECHANIZE_HTML)
    make_leaf_page(root, "robots.txt",
                   "User-Agent: *\nDisallow: /norobots",
                   "text/plain")
    make_leaf_page(root, "robots", "Hello, robots.", "text/plain")
    make_leaf_page(root, "norobots", "Hello, non-robots.", "text/plain")
    root.putChild(b'dynamic', DynamicPage())
    test_fixtures = make_page(root, "test_fixtures",
                              # satisfy stupid assertions in functional tests
                              html("Python bits",
                                   extra_content="GeneralFAQ.html"))
    make_leaf_page(test_fixtures, "cctest2.txt",
                   "Hello ClientCookie functional test suite.",
                   "text/plain")
    make_leaf_page(test_fixtures, "referertest.html", REFERER_TEST_HTML)
    make_leaf_page(test_fixtures, "mechanize_reload_test.html",
                   RELOAD_TEST_HTML)
    make_redirect(root, "redirected", b"/doesnotexist")
    make_redirect(root, "redirected_good", b"/test_fixtures")
    example_html = open(os.path.join(
        "examples", "forms", "example.html")).read()
    make_leaf_page(mechanize, "example.html", example_html)
    make_page(root, "basic_auth", BASIC_AUTH_PAGE, wrapper=require_basic_auth)
    make_page(root, "digest_auth", DIGEST_AUTH_PAGE,
              wrapper=require_digest_auth)
    make_leaf_page(
        root, "gzip", open(__file__).read(),
        "text/plain", wrapper=gzip_wrapper)

    site = server.Site(root)
    reactor.listenTCP(options.port, site)
    reactor.run()


if __name__ == "__main__":
    main(sys.argv)
