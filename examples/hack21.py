#/usr/bin/env python

# Port of Hack 21 from the O'Reilly book "Spidering Hacks" by Tara
# Calishain and Kevin Hemenway.  Of course, there's no need to explicitly
# catch exceptions in Python, unlike checking error return values in Perl,
# but I've left those in for the sake of a direct port.

import sys, os, re
from urllib2 import HTTPError

import mechanize
assert mechanize.__version__ >= (0, 0, 6, "a")

mech = mechanize.Browser()
#mech.set_debug_http(True)

# Get the starting search page
try:
    mech.open("http://search.cpan.org")
except HTTPError, e:
    sys.exit("%d: %s" % (e.code, e.msg))

# Select the form, fill the fields, and submit
mech.select_form(nr=0)
mech["query"] = "Lester"
mech["mode"] = ["author"]
try:
    mech.submit()
except HTTPError, e:
    sys.exit("post failed: %d: %s" % (e.code, e.msg))

# Find the link for "Andy"
try:
    mech.follow_link(text_regex=re.compile("Andy"))
except HTTPError, e:
    sys.exit("post failed: %d: %s" % (e.code, e.msg))

# Get all the tarballs
urls = [link.url for link in
        mech.links(url_regex=re.compile(r"\.tar\.gz$"))]
print "Found", len(urls), "tarballs to download"

for url in urls:
    filename = os.path.basename(url)
    f = file(filename, "wb")
    print "%s -->" % filename,
    r = mech.open(url)
    while 1:
        data = r.read(1024)
        if not data: break
        f.write(data)
    f.close()
    print os.stat(filename).st_size, "bytes"
