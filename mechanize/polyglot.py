#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

is_py2 = sys.version_info.major < 3

if is_py2:
    from urllib import urlencode
    from urllib2 import HTTPError
    from urlparse import urlsplit, urljoin, urlparse, urlunparse
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

    codepoint_to_chr = unichr


else:
    from urllib.error import HTTPError
    from urllib.parse import urlsplit, urljoin, urlparse, urlunparse, urlencode
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

    codepoint_to_chr = chr

if False:
    HTTPError, urlsplit, urljoin, urlparse, urlunparse, urlencode
    (DEFAULT_HTTP_PORT, CookiePolicy, DefaultCookiePolicy,
     FileCookieJar, LoadError, LWPCookieJar, _debug,
     domain_match, eff_request_host, escape_path, is_HDN,
     lwp_cookie_str, reach, request_path, request_port,
     user_domain_match, Cookie, CookieJar, MozillaCookieJar, request_host)
