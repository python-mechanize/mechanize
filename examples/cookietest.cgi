#!/usr/bin/python
# -*-python-*-

# The copy of this script that lives at wwwsearch.sf.net is used by the
# mechanize functional tests.

print "Content-Type: text/html"
print "Set-Cookie: foo=bar\n"
import sys, os, string, cgi, Cookie

from types import ListType

print "<html><head><title>Cookies and form submission parameters</title>"
cookie = Cookie.SimpleCookie()
cookieHdr = os.environ.get("HTTP_COOKIE", "")
cookie.load(cookieHdr)
if not cookie.has_key("foo"):
    print '<meta http-equiv="refresh" content="5">'
print "</head>"
print "<p>Received cookies:</p>"
print "<pre>"
print cgi.escape(os.environ.get("HTTP_COOKIE", ""))
print "</pre>"
if cookie.has_key("foo"):
    print "Your browser supports cookies!"
form = cgi.FieldStorage()
print "<p>Received parameters:</p>"
print "<pre>"
for k in form.keys():
    v = form[k]
    if isinstance(v, ListType):
        vs = []
        for item in v:
            vs.append(item.value)
        text = string.join(vs, ", ")
    else:
        text = v.value
    print "%s: %s" % (cgi.escape(k), cgi.escape(text))
print "</pre></html>"
