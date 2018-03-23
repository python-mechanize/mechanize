#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

is_py2 = sys.version_info.major < 3

if is_py2:
    import types
    from urllib import urlencode, pathname2url
    from urllib2 import HTTPError, URLError
    from robotparser import RobotFileParser
    from urlparse import urlsplit, urljoin, urlparse, urlunparse
    from httplib import HTTPMessage
    from cookielib import (
            DEFAULT_HTTP_PORT, CookiePolicy, DefaultCookiePolicy,
            FileCookieJar, LoadError, LWPCookieJar, _debug, domain_match,
            eff_request_host, escape_path, is_HDN, lwp_cookie_str, reach,
            request_path, request_port, user_domain_match, Cookie, CookieJar,
            MozillaCookieJar, request_host)

    def is_string(x):
        return isinstance(x, basestring)

    def iteritems(x):
        return x.iteritems()

    def is_class(obj):
        return isinstance(obj, (types.ClassType, type))

    codepoint_to_chr = unichr
    unicode_type = unicode


else:
    from urllib.error import HTTPError, URLError
    from urllib.robotparser import RobotFileParser
    from urllib.parse import urlsplit, urljoin, urlparse, urlunparse, urlencode
    from urllib.request import pathname2url
    from http.client import HTTPMessage
    from http.cookiejar import (
            DEFAULT_HTTP_PORT, CookiePolicy, DefaultCookiePolicy,
            FileCookieJar, LoadError, LWPCookieJar, _debug, domain_match,
            eff_request_host, escape_path, is_HDN, lwp_cookie_str, reach,
            request_path, request_port, user_domain_match, Cookie, CookieJar,
            MozillaCookieJar, request_host)

    def is_string(x):
        return isinstance(x, str)

    def iteritems(x):
        return x.items()

    def is_class(obj):
        return isinstance(obj, type)

    codepoint_to_chr = chr
    unicode_type = str

if False:
    HTTPError, urlsplit, urljoin, urlparse, urlunparse, urlencode, HTTPMessage
    pathname2url, RobotFileParser, URLError
    (DEFAULT_HTTP_PORT, CookiePolicy, DefaultCookiePolicy,
     FileCookieJar, LoadError, LWPCookieJar, _debug,
     domain_match, eff_request_host, escape_path, is_HDN,
     lwp_cookie_str, reach, request_path, request_port,
     user_domain_match, Cookie, CookieJar, MozillaCookieJar, request_host)
