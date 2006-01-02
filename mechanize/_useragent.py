"""Convenient HTTP UserAgent class.

This is a subclass of urllib2.OpenerDirector.


Copyright 2003-2006 John J. Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it under
the terms of the BSD License (see the file COPYING included with the
distribution).

"""

import sys
import urllib2, httplib
import ClientCookie
if sys.version_info[:2] >= (2, 4):
    import cookielib
    from urllib2 import OpenerDirector, BaseHandler, \
         HTTPHandler, HTTPErrorProcessor
    try:
        from urllib2 import HTTPSHandler
    except ImportError:
        pass
    class SaneHTTPCookieProcessor(ClientCookie.HTTPCookieProcessor):
        # Workaround for RFC 2109 bug http://python.org/sf/1157027 (at least if
        # you don't pass your own CookieJar in: if that's the case, you should
        # pass rfc2965=True to the DefaultCookiePolicy constructor yourself, or
        # set the corresponding attribute).
        def __init__(self, cookiejar=None):
            if cookiejar is None:
                cookiejar = cookielib.CookieJar(
                    cookielib.DefaultCookiePolicy(rfc2965=True))
            self.cookiejar = cookiejar
    HTTPCookieProcessor = SaneHTTPCookieProcessor
else:
    from ClientCookie import OpenerDirector, BaseHandler, \
         HTTPHandler, HTTPErrorProcessor, HTTPCookieProcessor
    try:
        from ClientCookie import HTTPSHandler
    except ImportError:
        pass

class HTTPRefererProcessor(BaseHandler):
    def http_request(self, request):
        # See RFC 2616 14.36.  The only times we know the source of the
        # request URI has a URI associated with it are redirect, and
        # Browser.click() / Browser.submit() / Browser.follow_link().
        # Otherwise, it's the user's job to add any Referer header before
        # .open()ing.
        if hasattr(request, "redirect_dict"):
            request = self.parent._add_referer_header(
                request, origin_request=False)
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
        "http": HTTPHandler,
        "ftp": urllib2.FTPHandler,  # CacheFTPHandler is buggy in 2.3
        "file": urllib2.FileHandler,
        "gopher": urllib2.GopherHandler,
        # XXX etc.

        # other handlers
        "_unknown": urllib2.UnknownHandler,
        # HTTP{S,}Handler depend on HTTPErrorProcessor too
        "_http_error": HTTPErrorProcessor,
        "_http_request_upgrade": ClientCookie.HTTPRequestUpgradeProcessor,
        "_http_default_error": urllib2.HTTPDefaultErrorHandler,

        # feature handlers
        "_authen": urllib2.HTTPBasicAuthHandler,
        # XXX rest of authentication stuff
        "_redirect": ClientCookie.HTTPRedirectHandler,
        "_cookies": HTTPCookieProcessor,
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
    default_features = ["_authen", "_redirect", "_cookies", "_refresh",
                        "_referer", "_equiv", "_seek", "_proxy"]
    if hasattr(httplib, 'HTTPS'):
        handler_classes["https"] = HTTPSHandler
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

        # Ensure correct default constructor args were passed to
        # HTTPRefererProcessor and HTTPEquivProcessor.  Yuck.
        if '_refresh' in self._ua_handlers:
            self.set_handle_refresh(True)
        if '_equiv' in self._ua_handlers:
            self.set_handle_equiv(True)

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

    def _add_referer_header(self, request, origin_request=True):
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
        """Set whether to handle HTTP 30x redirections."""
        self._set_handler("_redirect", handle)
    def set_handle_refresh(self, handle, max_time=None, honor_time=True):
        """Set whether to handle HTTP Refresh headers."""
        self._set_handler("_refresh", handle, constructor_kwds=
                          {"max_time": max_time, "honor_time": honor_time})
    def set_handle_equiv(self, handle, head_parser_class=None):
        """Set whether to treat HTML http-equiv headers like HTTP headers.

        Response objects will be .seek()able if this is set.

        """
        if head_parser_class is not None:
            constructor_kwds = {"head_parser_class": head_parser_class}
        else:
            constructor_kwds={}
        self._set_handler("_equiv", handle, constructor_kwds=constructor_kwds)
    def set_handle_referer(self, handle):
        """Set whether to add Referer header to each request.

        This base class does not implement this feature (so don't turn this on
        if you're using this base class directly), but the subclass
        mechanize.Browser does.

        """
        self._set_handler("_referer", handle)
        self._handle_referer = bool(handle)
    def set_seekable_responses(self, handle):
        """Make response objects .seek()able."""
        self._set_handler("_seek", handle)
    def set_debug_redirects(self, handle):
        """Log information about HTTP redirects.

        This includes refreshes, which show up as faked 302 redirections at the
        moment.

        Logs is performed using module logging.  The logger name is
        "ClientCookie.http_redirects".  To actually print some debug output,
        eg:

        logger = logging.getLogger("ClientCookie.http_redirects")
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.INFO)

        Other logger names relevant to this module:

        "ClientCookie.http_responses"
        "ClientCookie.cookies" (or "cookielib" if running Python 2.4)

        To turn on everything:

        for logger in [
            logging.getLogger("ClientCookie"),
            logging.getLogger("cookielib"),
            ]:
            logger.addHandler(logging.StreamHandler())
            logger.setLevel(logging.INFO)

        """
        self._set_handler("_debug_redirect", handle)
    def set_debug_responses(self, handle):
        """Log HTTP response bodies.

        See docstring for .set_debug_redirects() for details of logging.

        """
        self._set_handler("_debug_response_body", handle)
    def set_debug_http(self, handle):
        """Print HTTP headers to sys.stdout."""
        level = int(bool(handle))
        for scheme in "http", "https":
            h = self._ua_handlers.get(scheme)
            if h is not None:
                h.set_http_debuglevel(level)

    def _set_handler(self, name, handle=None, obj=None,
                     constructor_args=(), constructor_kwds={}):
        if handle is None:
            handle = obj is not None
        if handle:
            handler_class = self.handler_classes[name]
            if obj is not None:
                newhandler = handler_class(obj)
            else:
                newhandler = handler_class(*constructor_args, **constructor_kwds)
        else:
            newhandler = None
        self._replace_handler(name, newhandler)

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
