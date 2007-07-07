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

from twisted.web2 import server, http, resource, channel, \
     http_headers, responsecode, twcgi
from twisted.internet import reactor

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


class Page(resource.Resource):

  addSlash = True
  content_type = http_headers.MimeType("text", "html")

  def render(self, ctx):
    return http.Response(
        responsecode.OK,
        {"content-type": self.content_type},
        self.text)

def _make_page(parent, name, text,
              content_type="text/html",
              leaf=False):
    page = Page()
    page.text = text
    base_type, specific_type = content_type.split("/")
    page.content_type = http_headers.MimeType(base_type, specific_type)
    page.addSlash = not leaf
    setattr(parent, "child_"+name, page)
    return page

def make_page(parent, name, text,
              content_type="text/html"):
    return _make_page(parent, name, text, content_type, leaf=False)

def make_leaf_page(parent, name, text,
                   content_type="text/html"):
    return _make_page(parent, name, text, content_type, leaf=True)

def make_redirect(parent, name, location_relative_ref):
    redirect = resource.RedirectResource(path=location_relative_ref)
    setattr(parent, "child_"+name, redirect)
    return redirect

def make_cgi_bin(parent, name, dir_name):
    cgi_bin = twcgi.CGIDirectory(dir_name)
    setattr(parent, "child_"+name, cgi_bin)
    return cgi_bin

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

    site = server.Site(root)
    reactor.listenTCP(int(sys.argv[1]), channel.HTTPFactory(site))
    reactor.run()

main()
