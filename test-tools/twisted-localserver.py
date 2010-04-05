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

import optparse
import os
import re
import sys

from twisted.cred import portal, checkers
from twisted.internet import reactor
from twisted.python import log
from twisted.python.hashlib import md5
from twisted.web2 import server, http, resource, channel, \
     http_headers, responsecode, twcgi
from twisted.web2.auth import basic, digest, wrapper
from twisted.web2.auth.interfaces import IHTTPUser

from zope.interface import implements


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


class Dir(resource.Resource):

    addSlash = True

    def locateChild(self, request, segments):
        #import pdb; pdb.set_trace()
        return resource.Resource.locateChild(self, request, segments)

    def render(self, ctx):
        print "render"
        return http.Response(responsecode.FORBIDDEN)


def make_dir(parent, name):
    dir_ = Dir()
    parent.putChild(name, dir_)
    return dir_


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

def make_cgi_script(parent, name, path):
    cgi_script = twcgi.CGIScript(path)
    setattr(parent, "child_"+name, cgi_script)
    return cgi_script

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


class DigestCredFactory(digest.DigestCredentialFactory):

    def generateOpaque(self, nonce, clientip):
        # http://twistedmatrix.com/trac/ticket/3693
        key = "%s,%s,%s" % (nonce, clientip, str(int(self._getTime())))
        digest = md5(key + self.privateKey).hexdigest()
        ekey = key.encode('base64')
        return "%s-%s" % (digest, ekey.replace('\n', ''))


def require_digest_auth(resource):
    p = portal.Portal(TestAuthRealm())
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse()
    c.addUser("digestuser", "digestuser")
    p.registerChecker(c)
    cred_factory = DigestCredFactory("MD5", "Digest Auth protected area")
    return wrapper.HTTPAuthResource(resource,
                                    [cred_factory],
                                    p,
                                    interfaces=(IHTTPUser,))


def parse_options(args):
    parser = optparse.OptionParser()
    parser.add_option("--log", action="store_true")
    options, remaining_args = parser.parse_args(args)
    return options


def main(argv):
    options = parse_options(argv[1:])
    if options.log:
        log.startLogging(sys.stdout)

    # This is supposed to match the SF site so it's easy to run a functional
    # test over the internet and against Apache.
    # TODO: Remove bizarre structure and strings expected by functional tests.
    root = Page()
    root.text = ROOT_HTML
    mechanize = make_page(root, "mechanize", MECHANIZE_HTML)
    make_leaf_page(root, "robots.txt",
                   "User-Agent: *\nDisallow: /norobots",
                   "text/plain")
    make_leaf_page(root, "robots", "Hello, robots.", "text/plain")
    make_leaf_page(root, "norobots", "Hello, non-robots.", "text/plain")
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
    make_redirect(root, "redirected", "/doesnotexist")
    cgi_bin = make_dir(root, "cgi-bin")
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    make_cgi_script(cgi_bin, "cookietest.cgi",
                    os.path.join(project_dir, "test-tools", "cookietest.cgi"))
    example_html = open(os.path.join("examples", "forms", "example.html")).read()
    make_leaf_page(mechanize, "example.html", example_html)
    make_cgi_script(cgi_bin, "echo.cgi",
                    os.path.join(project_dir, "examples", "forms", "echo.cgi"))
    make_page(root, "basic_auth", BASIC_AUTH_PAGE, wrapper=require_basic_auth)
    make_page(root, "digest_auth", DIGEST_AUTH_PAGE,
              wrapper=require_digest_auth)

    site = server.Site(root)
    reactor.listenTCP(int(sys.argv[1]), channel.HTTPFactory(site))
    reactor.run()

main(sys.argv)
