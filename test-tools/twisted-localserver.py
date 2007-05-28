#!/usr/bin/env python
"""
%prog port

e.g. %prog 8000

Runs a local server to point the mechanize functional tests at.  Example:

python test-tools/twisted-localserver.py 8042
python functional_tests.py --uri=http://localhost:8042/

You need Twisted XXX version to run it:

XXX installation instructions
"""

import os, sys, re, time
from twisted.web2 import server, http, resource, channel, \
     static, http_headers, responsecode

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


class Page(resource.Resource):

  addSlash = True
  content_type = http_headers.MimeType("text", "html")

  def render(self, ctx):
    return http.Response(
        responsecode.OK,
        {"content-type": self.content_type},
        self.text)

def make_page(root, name, text,
              content_type="text/html"):
    page = Page()
    page.text = text
    base_type, specific_type = content_type.split("/")
    page.content_type = http_headers.MimeType(base_type, specific_type)
    setattr(root, "child_"+name, page)
    return page

def main():
    root = Page()
    root.text = ROOT_HTML
    make_page(root, "mechanize", MECHANIZE_HTML)
    bits = make_page(root, "robots.txt",
                     "User-Agent: *\nDisallow: /norobots",
                     "text/plain")
    bits = make_page(root, "robots", "Hello, robots.", "text/plain")
    bits = make_page(root, "norobots", "Hello, non-robots.", "text/plain")
    bits = make_page(root, "bits", "GeneralFAQ.html")
    make_page(bits, "cctest2.txt",
              "Hello ClientCookie functional test suite.",
              "text/plain")
    make_page(bits, "mechanize_reload_test.html", RELOAD_TEST_HTML)

    site = server.Site(root)
    reactor.listenTCP(int(sys.argv[1]), channel.HTTPFactory(site))
    reactor.run()

main()
