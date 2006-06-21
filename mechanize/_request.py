"""Integration with Python standard library module urllib2: Request class.

Copyright 2004-2006 John J Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

import urllib2
import urllib

from _clientcookie import request_host


class Request(urllib2.Request):
    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False):
        urllib2.Request.__init__(self, url, data, headers)
        self.selector = None
        self.unredirected_hdrs = {}

        # All the terminology below comes from RFC 2965.
        self.unverifiable = unverifiable
        # Set request-host of origin transaction.
        # The origin request-host is needed in order to decide whether
        # unverifiable sub-requests (automatic redirects, images embedded
        # in HTML, etc.) are to third-party hosts.  If they are, the
        # resulting transactions might need to be conducted with cookies
        # turned off.
        if origin_req_host is None:
            origin_req_host = request_host(self)
        self.origin_req_host = origin_req_host

    def get_selector(self):
        if self.selector is None:
            self.selector, self.__r_selector = urllib.splittag(self.__r_host)
        return self.selector

    def get_origin_req_host(self):
        return self.origin_req_host

    def is_unverifiable(self):
        return self.unverifiable

    def add_unredirected_header(self, key, val):
        """Add a header that will not be added to a redirected request."""
        self.unredirected_hdrs[key.capitalize()] = val

    def has_header(self, header_name):
        """True iff request has named header (regular or unredirected)."""
        return (header_name in self.headers or
                header_name in self.unredirected_hdrs)

    def get_header(self, header_name, default=None):
        return self.headers.get(
            header_name,
            self.unredirected_hdrs.get(header_name, default))

    def header_items(self):
        hdrs = self.unredirected_hdrs.copy()
        hdrs.update(self.headers)
        return hdrs.items()

    def __str__(self):
        return "<Request for %s>" % self.get_full_url()

    def get_method(self):
        if self.has_data():
            return "POST"
        else:
            return "GET"
