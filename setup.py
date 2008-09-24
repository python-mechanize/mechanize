#!/usr/bin/env python
"""Stateful programmatic web browsing.

Stateful programmatic web browsing, after Andy Lester's Perl module
WWW::Mechanize.

The library is layered: mechanize.Browser (stateful web browser),
mechanize.UserAgent (configurable URL opener), plus urllib2 handlers.

Features include: ftp:, http: and file: URL schemes, browser history,
high-level hyperlink and HTML form support, HTTP cookies, HTTP-EQUIV and
Refresh, Referer [sic] header, robots.txt, redirections, proxies, and
Basic and Digest HTTP authentication.  mechanize's response objects are
(lazily-) .seek()able and still work after .close().

Much of the code originally derived from Perl code by Gisle Aas
(libwww-perl), Johnny Lee (MSIE Cookie support) and last but not least
Andy Lester (WWW::Mechanize).  urllib2 was written by Jeremy Hylton.

"""

def unparse_version(tup):
    major, minor, bugfix, state_char, pre = tup
    fmt = "%s.%s.%s"
    args = [major, minor, bugfix]
    if state_char is not None:
        fmt += "%s"
        args.append(state_char)
    if pre is not None:
        fmt += "-pre%s"
        args.append(pre)
    return fmt % tuple(args)

def str_to_tuple(text):
    if text.startswith("("):
        text = text[1:-1]
    els = [el.strip() for el in text.split(",")]
    newEls = []
    for ii in range(len(els)):
        el = els[ii]
        if el == "None":
            newEls.append(None)
        elif 0 <= ii < 3:
            newEls.append(int(el))
        else:
            if el.startswith("'") or el.startswith('"'):
                el = el[1:-1]
            newEls.append(el)
    return tuple(newEls)

import re
## VERSION_MATCH = re.search(r'__version__ = \((.*)\)',
##                           open("mechanize/_mechanize.py").read())
## VERSION = unparse_version(str_to_tuple(VERSION_MATCH.group(1)))
VERSION = "0.1.9"
INSTALL_REQUIRES = ["ClientForm>=0.2.6, ==dev"]
NAME = "mechanize"
PACKAGE = True
LICENSE = "BSD"  # or ZPL 2.1
PLATFORMS = ["any"]
ZIP_SAFE = True
CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
Intended Audience :: System Administrators
License :: OSI Approved :: BSD License
License :: OSI Approved :: Zope Public License
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Topic :: Internet
Topic :: Internet :: File Transfer Protocol (FTP)
Topic :: Internet :: WWW/HTTP
Topic :: Internet :: WWW/HTTP :: Browsers
Topic :: Internet :: WWW/HTTP :: Indexing/Search
Topic :: Internet :: WWW/HTTP :: Site Management
Topic :: Internet :: WWW/HTTP :: Site Management :: Link Checking
Topic :: Software Development :: Libraries
Topic :: Software Development :: Libraries :: Python Modules
Topic :: Software Development :: Testing
Topic :: Software Development :: Testing :: Traffic Generation
Topic :: System :: Archiving :: Mirroring
Topic :: System :: Networking :: Monitoring
Topic :: System :: Systems Administration
Topic :: Text Processing
Topic :: Text Processing :: Markup
Topic :: Text Processing :: Markup :: HTML
Topic :: Text Processing :: Markup :: XML
"""

#-------------------------------------------------------
# the rest is constant for most of my released packages:

import sys

if PACKAGE:
    packages, py_modules = [NAME], None
else:
    packages, py_modules = None, [NAME]

doclines = __doc__.split("\n")

if not hasattr(sys, "version_info") or sys.version_info < (2, 3):
    from distutils.core import setup
    _setup = setup
    def setup(**kwargs):
        for key in [
            # distutils >= Python 2.3 args
            # XXX probably download_url came in earlier than 2.3
            "classifiers", "download_url",
            # setuptools args
            "install_requires", "zip_safe", "test_suite",
            ]:
            if kwargs.has_key(key):
                del kwargs[key]
        # Only want packages keyword if this is a package,
        # only want py_modules keyword if this is a single-file module,
        # so get rid of packages or py_modules keyword as appropriate.
        if kwargs["packages"] is None:
            del kwargs["packages"]
        else:
            del kwargs["py_modules"]
        apply(_setup, (), kwargs)
else:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup

setup(
    name = NAME,
    version = VERSION,
    license = LICENSE,
    platforms = PLATFORMS,
    classifiers = [c for c in CLASSIFIERS.split("\n") if c],
    install_requires = INSTALL_REQUIRES,
    zip_safe = ZIP_SAFE,
    test_suite = "test",
    author = "John J. Lee",
    author_email = "jjl@pobox.com",
    description = doclines[0],
    long_description = "\n".join(doclines[2:]),
    url = "http://wwwsearch.sourceforge.net/%s/" % NAME,
    download_url = ("http://wwwsearch.sourceforge.net/%s/src/"
                    "%s-%s.tar.gz" % (NAME, NAME, VERSION)),
    py_modules = py_modules,
    packages = packages,
    )
