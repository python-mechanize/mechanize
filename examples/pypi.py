#!/usr/bin/env python

# Search PyPI, the Python Package Index, and retrieve latest mechanize
# tarball.

# This is just illustrative: I assume there's an easier way of doing
# this (also note that the download field doesn't in general point
# directly to the source, and that many packages (including mine!)
# aren't yet registered religiouly at every release).

import sys, os, re

import mechanize

b = mechanize.Browser()

# search PyPI
b.open("http://www.python.org/pypi")
b.follow_link(text="Search", nr=1)
b.select_form(nr=0)
b["name"] = "mechanize"
b.submit()

# find latest release
VERSION_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<bugfix>\d+)"
                        r"(?P<state>[ab])?(?:-pre)?(?P<pre>\d+)?$")
def parse_version(text):
    m = VERSION_RE.match(text)
    if m is None:
        raise ValueError
    return tuple([m.groupdict()[part] for part in
                  ("major", "minor", "bugfix", "state", "pre")])
MECHANIZE_RE = re.compile(r"mechanize-?(.*)")
links = b.links(text_regex=MECHANIZE_RE)
versions = []
for link in links:
    m = MECHANIZE_RE.search(link.text)
    version_string = m.group(1).strip()
    tup = parse_version(version_string)[:3]
    versions.append(tup)
latest = links[versions.index(max(versions))]

# get tarball
b.follow_link(latest)  # to PKG-INFO page
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
