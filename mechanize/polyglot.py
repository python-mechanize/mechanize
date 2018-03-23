#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

is_py2 = sys.version_info.major < 3

if is_py2:
    from urllib2 import HTTPError
    from urlparse import urlsplit
else:
    from urllib.error import HTTPError
    from urllib.parse import urlsplit
if False:
    HTTPError, urlsplit
