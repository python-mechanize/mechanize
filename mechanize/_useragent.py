"""Convenient HTTP UserAgent class.

This is a subclass of urllib2.OpenerDirector.


Copyright 2003 John J. Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it under
the terms of the BSD License (see the file COPYING included with the
distribution).

"""

import urllib2, httplib
import ClientCookie
from ClientCookie import OpenerDirector, BaseHandler

class HTTPRefererProcessor(BaseHandler):
    def http_request(self, request):
        # See RFC 2616 14.36.  The only times we know the source of the
        # request URI has a URI associated with it are redirect, and
        # Browser.click() / Browser.submit() / Browser.follow_link().
        # Otherwise, it's the user's job to add any Referer header before
        # .open()ing.
        if hasattr(request, "redirect_dict"):
            request = self.parent._add_referer_header(request)
        return request

    https_request = http_request


class UserAgent(OpenerDirector):
    """Convenient user-agent class.

    Do not use .add_handler() to add a handler for something already dealt with
    by this code.

    Public attributes:

    addheaders: list of (name, value) pairs specifying headers to send with
     every request, unless they are overridden in the Request instance.

     >>> ua = UserAgent()
     >>> ua.addheaders = [
     ...  ("User-agent", "Mozilla/5.0 (compatible)"),
     ...  ("From", "responsible.person@example.com")]

    """

    handler_classes = {
        # scheme handlers
        "http": ClientCookie.HTTPHandler,
        "ftp": urllib2.FTPHandler,  # CacheFTPHandler is buggy in 2.3
        "file": urllib2.FileHandler,
        "gopher": urllib2.GopherHandler,
        # XXX etc.

        # other handlers
        "_unknown": urllib2.UnknownHandler,
        # HTTP{S,}Handler depend on HTTPErrorProcessor too
        "_http_error": ClientCookie.HTTPErrorProcessor,
        "_http_request_upgrade": ClientCookie.HTTPRequestUpgradeProcessor,
        "_http_default_error": urllib2.HTTPDefaultErrorHandler,

        # feature handlers
        "_authen": urllib2.HTTPBasicAuthHandler,
        # XXX rest of authentication stuff
        "_redirect": ClientCookie.HTTPRedirectHandler,
        "_cookies": ClientCookie.HTTPCookieProcessor,
        "_refresh": ClientCookie.HTTPRefreshProcessor,
        "_referer": HTTPRefererProcessor,  # from this module, note
        "_equiv": ClientCookie.HTTPEquivProcessor,
        "_seek": ClientCookie.SeekableProcessor,
        "_proxy": urllib2.ProxyHandler,
        # XXX there's more to proxies, too

        # debug handlers
        "_debug_redirect": ClientCookie.HTTPRedirectDebugProcessor,
        "_debug_response_body": ClientCookie.HTTPResponseDebugProcessor,
        }

    default_schemes = ["http", "ftp", "file", "gopher"]
    default_others = ["_unknown", "_http_error", "_http_request_upgrade",
                      "_http_default_error"]
    default_features = ["_authen", "_redirect", "_cookies", "_seek", "_proxy"]
    if hasattr(httplib, 'HTTPS'):
        handler_classes["https"] = ClientCookie.HTTPSHandler
        default_schemes.append("https")
    if hasattr(ClientCookie, "HTTPRobotRulesProcessor"):
        handler_classes["_robots"] = ClientCookie.HTTPRobotRulesProcessor
        default_features.append("_robots")

    def __init__(self):
        OpenerDirector.__init__(self)

        self._ua_handlers = {}
        for scheme in (self.default_schemes+
                       self.default_others+
                       self.default_features):
            klass = self.handler_classes[scheme]
            self._ua_handlers[scheme] = klass()
        for handler in self._ua_handlers.itervalues():
            self.add_handler(handler)

        # special case, requires extra support from mechanize.Browser
        self._handle_referer = True

    def close(self):
        OpenerDirector.close(self)
        self._ua_handlers = None

    # XXX
##     def set_timeout(self, timeout):
##         self._timeout = timeout
##     def set_http_connection_cache(self, conn_cache):
##         self._http_conn_cache = conn_cache
##     def set_ftp_connection_cache(self, conn_cache):
##         # XXX ATM, FTP has cache as part of handler; should it be separate?
##         self._ftp_conn_cache = conn_cache

    def set_handled_schemes(self, schemes):
        """Set sequence of protocol scheme strings.

        If this fails (with ValueError) because you've passed an unknown
        scheme, the set of handled schemes WILL be updated, but schemes in the
        list that come after the unknown scheme won't be handled.

        """
        want = {}
        for scheme in schemes:
            if scheme.startswith("_"):
                raise ValueError("invalid scheme '%s'" % scheme)
            want[scheme] = None

        # get rid of scheme handlers we don't want
        for scheme, oldhandler in self._ua_handlers.items():
            if scheme.startswith("_"): continue  # not a scheme handler
            if scheme not in want:
                self._replace_handler(scheme, None)
            else:
                del want[scheme]  # already got it
        # add the scheme handlers that are missing
        for scheme in want.keys():
            if scheme not in self.handler_classes:
                raise ValueError("unknown scheme '%s'")
            self._set_handler(scheme, True)

    def _add_referer_header(self, request):
        raise NotImplementedError(
            "this class can't do HTTP Referer: use mechanize.Browser instead")

    def set_cookiejar(self, cookiejar):
        """Set a ClientCookie.CookieJar, or None."""
        self._set_handler("_cookies", obj=cookiejar)
    def set_credentials(self, credentials):
        """Set a urllib2.HTTPPasswordMgr, or None."""
        # XXX use Greg Stein's httpx instead?
        self._set_handler("_authen", obj=credentials)

    # these methods all take a boolean parameter
    def set_handle_robots(self, handle):
        """Set whether to observe rules from robots.txt."""
        self._set_handler("_robots", handle)
    def set_handle_redirect(self, handle):
        """Set whether to handle HTTP Refresh headers."""
        self._set_handler("_redirect", handle)
    def set_handle_refresh(self, handle):
        """Set whether to handle HTTP Refresh headers."""
        self._set_handler("_refresh", handle)
    def set_handle_equiv(self, handle):
        """Set whether to treat HTML http-equiv headers like HTTP headers.

        Response objects will be .seek()able if this is set.

        """
        self._set_handler("_equiv", handle)
    def set_handle_referer(self, handle):
        """Set whether to add Referer header to each request.

        This base class does not implement this feature (so don't turn this on
        if you're using this base class directly), but the subclass
        mechanize.Browser does.

        """
        self._set_handler("_referer", handle)
        self._handle_referer = True
    def set_seekable_responses(self, handle):
        """Make response objects .seek()able."""
        self._set_handler("_seek", handle)
    def set_debug_redirects(self, handle):
        """Print information about HTTP redirects.

        This includes refreshes, which show up as faked 302 redirections at the
        moment.

        """
        self._set_handler("_debug_redirect", handle)
    def set_debug_responses(self, handle):
        """Print HTTP response bodies."""
        self._set_handler("_debug_response_body", handle)
    def set_debug_http(self, handle):
        """Print HTTP headers."""
        level = int(bool(handle))
        for scheme in "http", "https":
            h = self._ua_handlers.get(scheme)
            if h is not None:
                h.set_http_debuglevel(level)

    def _set_handler(self, name, handle=None, obj=None):
        if handle is None:
            handle = obj is not None
        if handle:
            handler_class = self.handler_classes[name]
            if obj is not None:
                newhandler = handler_class(obj)
            else:
                newhandler = handler_class()
        else:
            newhandler = None
        self._replace_handler(name, newhandler)

    # XXXX I'd *really* rather get rid of this and just rebuild every time.
    #  This is fragile to base class changes, and hard to understand.
    #  Have to make sure there's no state directly stored in handlers, though,
    #  and have appropriate methods for adding state back to the cookie etc.
    #  handlers known to this class (only the ones in urllib2 / ClientCookie --
    #  no need to care about other peoples' as long as it's documented that
    #  calling the set_* methods will in general clobber handler state).
    def _replace_handler(self, name, newhandler=None):
        # first, if handler was previously added, remove it
        if name is not None:
            try:
                handler = self._ua_handlers[name]
            except:
                pass
            else:
                for table in (
                    [self.handle_open,
                     self.process_request, self.process_response]+
                    self.handle_error.values()):
                    for handlers in table.values():
                        remove(handlers, handler)
                    remove(self.handlers, handler)
        # then add the replacement, if any
        if newhandler is not None:
            self.add_handler(newhandler)
            self._ua_handlers[name] = newhandler

def remove(sequence, obj):
    # for use when can't use .remove() because of obj.__cmp__ :-(
    # (ClientCookie only requires Python 2.0, which doesn't have __lt__)
    i = 0
    while i < len(sequence):
        if sequence[i] is obj:
            del sequence[i]
        else:
            i += 1

# XXX
# This is urllib2.Request with a new .set_method() method,
# for HTTP HEAD / PUT -- move into ClientCookie if/when need it.
# Maybe it should have a constructor arg, too.
## class Request:

##     def __init__(self, url, data=None, headers={}):
##         # unwrap('<URL:type://host/path>') --> 'type://host/path'
##         self.__original = unwrap(url)
##         self.type = None
##         # self.__r_type is what's left after doing the splittype
##         self.host = None
##         self.port = None
##         self.data = data
##         self.headers = {}
##         for key, value in headers.items():
##             self.add_header(key, value)
##         if data is None:
##             self._method = "GET"
##         else:
##             self._method = "POST"

##     def __getattr__(self, attr):
##         # XXX this is a fallback mechanism to guard against these
##         # methods getting called in a non-standard order.  this may be
##         # too complicated and/or unnecessary.
##         # XXX should the __r_XXX attributes be public?
##         if attr[:12] == '_Request__r_':
##             name = attr[12:]
##             if hasattr(Request, 'get_' + name):
##                 getattr(self, 'get_' + name)()
##                 return getattr(self, attr)
##         raise AttributeError, attr

##     def get_method(self):
##         return self._method

##     def set_method(self, method):
##         if method == "POST":
##             if data is None:
##                 data = ""
##         else:
##             self.data = None
##         self._method == method

##     def add_data(self, data):
##         self.data = data

##     def has_data(self):
##         return self.data is not None

##     def get_data(self):
##         return self.data

##     def get_full_url(self):
##         return self.__original

##     def get_type(self):
##         if self.type is None:
##             self.type, self.__r_type = splittype(self.__original)
##             if self.type is None:
##                 raise ValueError, "unknown url type: %s" % self.__original
##         return self.type

##     def get_host(self):
##         if self.host is None:
##             self.host, self.__r_host = splithost(self.__r_type)
##             if self.host:
##                 self.host = unquote(self.host)
##         return self.host

##     def get_selector(self):
##         return self.__r_host

##     def set_proxy(self, host, type):
##         self.host, self.type = host, type
##         self.__r_host = self.__original

##     def add_header(self, key, val):
##         # useful for something like authentication
##         self.headers[key.capitalize()] = val


## def http_get(fullurl, ranges=None, conditions=None):
##     """HTTP GET, with convenient partial fetches (ranges).

##     XXX conditional fetches?

##     ranges: sequence of pairs of byte ranges (start, end) to fetch;

##     Ranges follow the usual Python rules (the start byte is included,
##     the end byte is not; negative numbers count back from the end of
##     the entity; start None means start of entity; end None means end of
##     entity).  There are restrictions, though: end must not be negative,
##     and if start is negative, end must be None.

##     >>> http_get("http://www.example.com/big.dat",
##                  [(0, 10), (-10, None)])  # first and last 10 bytes
##     >>> http_get("http://www.example.com/big.dat",
##                  [(50000, None)])  # from byte 50000 to the end

##     """
##     if conditions: raise NotImplementedError("conditions not yet implemented")
##     req = self._request(fullurl, data)
##     assert req.get_type() == "http", "http_get for non-HTTP URI"
##     rs = []
##     for start, end in ranges:
##         if start < 0:
##             assert end is None, "invalid range"
##             start = ""
##         else:
##             assert 0 <= start <= end, "invalid range"
##             if start == end: continue
##             end = end - 1
##         rs.append("%s-%s" % range)
##     req.add_header(("Range", "bytes=" % string.join(rs, ", ")))
##     return self.open(req)

## def http_head(self, fullurl):
##     raise NotImplementedError()  # XXX

## def http_put(self, fullurl, data=None):
##     # XXX what about 30x handling?
##     raise NotImplementedError()  # XXX
