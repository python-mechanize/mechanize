"""Integration with Python standard library module urllib2: OpenerDirector
class.

Copyright 2004-2006 John J Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

import urllib2, string, bisect, urlparse

from _Util import startswith, isstringlike
from _Request import Request

def methnames(obj):
    """Return method names of class instance.

    dir(obj) doesn't work across Python versions, this does.

    """
    return methnames_of_instance_as_dict(obj).keys()

def methnames_of_instance_as_dict(inst):
    names = {}
    names.update(methnames_of_class_as_dict(inst.__class__))
    for methname in dir(inst):
        candidate = getattr(inst, methname)
        if callable(candidate):
            names[methname] = None
    return names

def methnames_of_class_as_dict(klass):
    names = {}
    for methname in dir(klass):
        candidate = getattr(klass, methname)
        if callable(candidate):
            names[methname] = None
    for baseclass in klass.__bases__:
        names.update(methnames_of_class_as_dict(baseclass))
    return names


class OpenerDirector(urllib2.OpenerDirector):
    def __init__(self):
        urllib2.OpenerDirector.__init__(self)
        self.process_response = {}
        self.process_request = {}

    def add_handler(self, handler):
        added = False
        for meth in methnames(handler):
            i = string.find(meth, "_")
            protocol = meth[:i]
            condition = meth[i+1:]

            if startswith(condition, "error"):
                j = string.find(meth[i+1:], "_") + i + 1
                kind = meth[j+1:]
                try:
                    kind = int(kind)
                except ValueError:
                    pass
                lookup = self.handle_error.get(protocol, {})
                self.handle_error[protocol] = lookup
            elif (condition == "open" and
                  protocol not in ["do", "proxy"]):  # hack -- see below
                kind = protocol
                lookup = self.handle_open
            elif (condition in ["response", "request"] and
                  protocol != "redirect"):  # yucky hack
                # hack above is to fix HTTPRedirectHandler problem, which
                # appears to above line to be a processor because of the
                # redirect_request method :-((
                kind = protocol
                lookup = getattr(self, "process_"+condition)
            else:
                continue

            if lookup.has_key(kind):
                bisect.insort(lookup[kind], handler)
            else:
                lookup[kind] = [handler]
            added = True

        if added:
            # XXX why does self.handlers need to be sorted?
            bisect.insort(self.handlers, handler)
            handler.add_parent(self)

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

        # pre-process request
        # XXX should we allow a Processor to change the type (URL
        #   scheme) of the request?
        for scheme in ["any", req_scheme]:
            meth_name = scheme+"_request"
            for processor in self.process_request.get(scheme, []):
                meth = getattr(processor, meth_name)
                req = meth(req)

        # In Python >= 2.4, .open() supports processors already, so we must
        # call ._open() instead.
        urlopen = getattr(urllib2.OpenerDirector, "_open",
                          urllib2.OpenerDirector.open)
        response = urlopen(self, req, data)

        # post-process response
        for scheme in ["any", req_scheme]:
            meth_name = scheme+"_response"
            for processor in self.process_response.get(scheme, []):
                meth = getattr(processor, meth_name)
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
