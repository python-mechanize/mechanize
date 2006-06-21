"""Integration with Python standard library module urllib2: OpenerDirector
class.

Copyright 2004-2006 John J Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

import urllib2, bisect, urlparse, httplib, types
try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading
try:
    set
except NameError:
    import sets
    set = sets.Set

import _http
import _upgrade
from _util import isstringlike
from _request import Request


class OpenerDirector(urllib2.OpenerDirector):
    def __init__(self):
        urllib2.OpenerDirector.__init__(self)
        # really none of these are (sanely) public -- the lack of initial
        # underscore on some is just due to following urllib2
        self.process_response = {}
        self.process_request = {}
        self._any_request = {}
        self._any_response = {}
        self._handler_index_valid = True

    def add_handler(self, handler):
        if handler in self.handlers:
            return
        # XXX why does self.handlers need to be sorted?
        bisect.insort(self.handlers, handler)
        handler.add_parent(self)
        self._handler_index_valid = False

    def _maybe_reindex_handlers(self):
        if self._handler_index_valid:
            return

        handle_error = {}
        handle_open = {}
        process_request = {}
        process_response = {}
        any_request = set()
        any_response = set()
        unwanted = []

        for handler in self.handlers:
            added = False
            for meth in dir(handler):
                if meth in ["redirect_request", "do_open", "proxy_open"]:
                    # oops, coincidental match
                    continue

                if meth == "any_request":
                    any_request.add(handler)
                    added = True
                    continue
                elif meth == "any_response":
                    any_response.add(handler)
                    added = True
                    continue

                ii = meth.find("_")
                scheme = meth[:ii]
                condition = meth[ii+1:]

                if condition.startswith("error"):
                    jj = meth[ii+1:].find("_") + ii + 1
                    kind = meth[jj+1:]
                    try:
                        kind = int(kind)
                    except ValueError:
                        pass
                    lookup = handle_error.setdefault(scheme, {})
                elif condition == "open":
                    kind = scheme
                    lookup = handle_open
                elif condition == "request":
                    kind = scheme
                    lookup = process_request
                elif condition == "response":
                    kind = scheme
                    lookup = process_response
                else:
                    continue

                lookup.setdefault(kind, set()).add(handler)
                added = True

            if not added:
                unwanted.append(handler)

        for handler in unwanted:
            self.handlers.remove(handler)

        # sort indexed methods
        # XXX could be cleaned up
        for lookup in [process_request, process_response]:
            for scheme, handlers in lookup.iteritems():
                lookup[scheme] = handlers
        for scheme, lookup in handle_error.iteritems():
            for code, handlers in lookup.iteritems():
                handlers = list(handlers)
                handlers.sort()
                lookup[code] = handlers
        for scheme, handlers in handle_open.iteritems():
            handlers = list(handlers)
            handlers.sort()
            handle_open[scheme] = handlers

        # cache the indexes
        self.handle_error = handle_error
        self.handle_open = handle_open
        self.process_request = process_request
        self.process_response = process_response
        self._any_request = any_request
        self._any_response = any_response

    def _request(self, url_or_req, data):
        if isstringlike(url_or_req):
            req = Request(url_or_req, data)
        else:
            # already a urllib2.Request or mechanize.Request instance
            req = url_or_req
            if data is not None:
                req.add_data(data)
        return req

    def open(self, fullurl, data=None):
        req = self._request(fullurl, data)
        req_scheme = req.get_type()

        self._maybe_reindex_handlers()

        # pre-process request
        # XXX should we allow a Processor to change the URL scheme
        #   of the request?
        request_processors = set(self.process_request.get(req_scheme, []))
        request_processors.update(self._any_request)
        request_processors = list(request_processors)
        request_processors.sort()
        for processor in request_processors:
            for meth_name in ["any_request", req_scheme+"_request"]:
                meth = getattr(processor, meth_name, None)
                if meth:
                    req = meth(req)

        # In Python >= 2.4, .open() supports processors already, so we must
        # call ._open() instead.
        urlopen = getattr(urllib2.OpenerDirector, "_open",
                          urllib2.OpenerDirector.open)
        response = urlopen(self, req, data)

        # post-process response
        response_processors = set(self.process_response.get(req_scheme, []))
        response_processors.update(self._any_response)
        response_processors = list(response_processors)
        response_processors.sort()
        for processor in response_processors:
            for meth_name in ["any_response", req_scheme+"_response"]:
                meth = getattr(processor, meth_name, None)
                if meth:
                    response = meth(req, response)

        return response

    def error(self, proto, *args):
        if proto in ['http', 'https']:
            # XXX http[s] protocols are special-cased
            dict = self.handle_error['http'] # https is not different than http
            proto = args[2]  # YUCK!
            meth_name = 'http_error_%s' % proto
            http_err = 1
            orig_args = args
        else:
            dict = self.handle_error
            meth_name = proto + '_error'
            http_err = 0
        args = (dict, proto, meth_name) + args
        result = apply(self._call_chain, args)
        if result:
            return result

        if http_err:
            args = (dict, 'default', 'http_error_default') + orig_args
            return apply(self._call_chain, args)

    def retrieve(self, fullurl, filename=None, reporthook=None, data=None):
        """Returns (filename, headers).

        For remote objects, the default filename will refer to a temporary
        file.

        """
        req = self._request(fullurl, data)
        type_ = req.get_type()
        fp = self.open(req)
        headers = fp.info()
        if filename is None and type == 'file':
            return url2pathname(req.get_selector()), headers
        if filename:
            tfp = open(filename, 'wb')
        else:
            path = urlparse(fullurl)[2]
            suffix = os.path.splitext(path)[1]
            tfp = tempfile.TemporaryFile("wb", suffix=suffix)
        result = filename, headers
        bs = 1024*8
        size = -1
        read = 0
        blocknum = 1
        if reporthook:
            if headers.has_key("content-length"):
                size = int(headers["Content-Length"])
            reporthook(0, bs, size)
        while 1:
            block = fp.read(bs)
            read += len(block)
            if reporthook:
                reporthook(blocknum, bs, size)
            blocknum = blocknum + 1
            if not block:
                break
            tfp.write(block)
        fp.close()
        tfp.close()
        del fp
        del tfp
        if size>=0 and read<size:
            raise IOError("incomplete retrieval error",
                          "got only %d bytes out of %d" % (read,size))
        return result


class OpenerFactory:
    """This class's interface is quite likely to change."""

    default_classes = [
        # handlers
        urllib2.ProxyHandler,
        urllib2.UnknownHandler,
        _http.HTTPHandler,  # derived from new AbstractHTTPHandler
        urllib2.HTTPDefaultErrorHandler,
        _http.HTTPRedirectHandler,  # bugfixed
        urllib2.FTPHandler,
        urllib2.FileHandler,
        # processors
        _upgrade.HTTPRequestUpgradeProcessor,
        _http.HTTPCookieProcessor,
        _http.HTTPErrorProcessor,
        ]
    if hasattr(httplib, 'HTTPS'):
        default_classes.append(_http.HTTPSHandler)
    handlers = []
    replacement_handlers = []

    def __init__(self, klass=OpenerDirector):
        self.klass = klass

    def build_opener(self, *handlers):
        """Create an opener object from a list of handlers and processors.

        The opener will use several default handlers and processors, including
        support for HTTP and FTP.

        If any of the handlers passed as arguments are subclasses of the
        default handlers, the default handlers will not be used.

        """
        opener = self.klass()
        default_classes = list(self.default_classes)
        skip = []
        for klass in default_classes:
            for check in handlers:
                if type(check) == types.ClassType:
                    if issubclass(check, klass):
                        skip.append(klass)
                elif type(check) == types.InstanceType:
                    if isinstance(check, klass):
                        skip.append(klass)
        for klass in skip:
            default_classes.remove(klass)

        for klass in default_classes:
            opener.add_handler(klass())
        for h in handlers:
            if type(h) == types.ClassType:
                h = h()
            opener.add_handler(h)

        return opener


build_opener = OpenerFactory().build_opener

_opener = None
urlopen_lock = _threading.Lock()
def urlopen(url, data=None):
    global _opener
    if _opener is None:
        urlopen_lock.acquire()
        try:
            if _opener is None:
                _opener = build_opener()
        finally:
            urlopen_lock.release()
    return _opener.open(url, data)

def urlretrieve(url, filename=None, reporthook=None, data=None):
    global _opener
    if _opener is None:
        urlopen_lock.acquire()
        try:
            if _opener is None:
                _opener = build_opener()
        finally:
            urlopen_lock.release()
    return _opener.retrieve(url, filename, reporthook, data)

def install_opener(opener):
    global _opener
    _opener = opener
