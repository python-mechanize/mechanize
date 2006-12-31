#!/usr/bin/env python

# ------------------------------------------------------------------------
# THIS SCRIPT IS CURRENTLY NOT WORKING, SINCE PYPI's SEARCH FEATURE HAS
# BEEN REMOVED!
# ------------------------------------------------------------------------

# Search PyPI, the Python Package Index, and retrieve latest mechanize
# tarball.

# This is just to demonstrate mechanize: You should use EasyInstall to
# do this, not this silly script.

import sys, os, re

import mechanize

b = mechanize.Browser(
    # mechanize's XHTML support needs work, so is currently switched off.  If
    # we want to get our work done, we have to turn it on by supplying a
    # mechanize.Factory (with XHTML support turned on):
    factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
    )
# Addition 2005-06-13: Be naughty, since robots.txt asks not to
# access /pypi now.  We're not madly searching for everything, so
# I don't feel too guilty.
b.set_handle_robots(False)

# search PyPI
b.open("http://www.python.org/pypi")
b.follow_link(text="Search", nr=1)
b.select_form(nr=0)
b["name"] = "mechanize"
b.submit()

# 2005-05-20 no longer necessary, only one version there, so PyPI takes
# us direct to PKG-INFO page
## # find latest release
## VERSION_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<bugfix>\d+)"
##                         r"(?P<state>[ab])?(?:-pre)?(?P<pre>\d+)?$")
## def parse_version(text):
##     m = VERSION_RE.match(text)
##     if m is None:
##         raise ValueError
##     return tuple([m.groupdict()[part] for part in
##                   ("major", "minor", "bugfix", "state", "pre")])
## MECHANIZE_RE = re.compile(r"mechanize-?(.*)")
## links = b.links(text_regex=MECHANIZE_RE)
## versions = []
## for link in links:
##     m = MECHANIZE_RE.search(link.text)
##     version_string = m.group(1).strip(' \t\xa0')
##     tup = parse_version(version_string)[:3]
##     versions.append(tup)
## latest = links[versions.index(max(versions))]

# get tarball
## b.follow_link(latest)  # to PKG-INFO page
r = b.follow_link(text_regex=re.compile(r"\.tar\.gz"))
filename = os.path.basename(b.geturl())
if os.path.exists(filename):
    sys.exit("%s already exists, not grabbing" % filename)
f = file(filename, "wb")
while 1:
    data = r.read(1024)
    if not data: break
    f.write(data)
f.close()
