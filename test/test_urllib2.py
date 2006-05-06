"""Tests for ClientCookie._urllib2_support (and for urllib2)."""

# XXX
# Request (I'm too lazy)
# CacheFTPHandler (hard to write)
# parse_keqv_list, parse_http_list (I'm leaving this for Anthony Baxter
#  and Greg Stein, since they're doing Digest Authentication)
# Authentication stuff (ditto)
# ProxyHandler, CustomProxy, CustomProxyHandler (I don't use a proxy)
# GopherHandler (haven't used gopher for a decade or so...)

import unittest, StringIO, os, sys, UserDict

import urllib2
from ClientCookie._urllib2_support import Request, AbstractHTTPHandler, \
     build_opener, parse_head, urlopen
from ClientCookie._Util import startswith
from ClientCookie import HTTPRedirectHandler, HTTPRequestUpgradeProcessor, \
     HTTPEquivProcessor, HTTPRefreshProcessor, SeekableProcessor, \
     HTTPCookieProcessor, HTTPRefererProcessor, \
     HTTPErrorProcessor, HTTPHandler
from ClientCookie import OpenerDirector

try: True
except NameError:
    True = 1
    False = 0

## from ClientCookie import getLogger, DEBUG
## l = getLogger("ClientCookie")
## l.setLevel(DEBUG)

class MockOpener:
    addheaders = []
    def open(self, req, data=None):
        self.req, self.data = req, data
    def error(self, proto, *args):
        self.proto, self.args = proto, args

class MockFile:
    def read(self, count=None): pass
    def readline(self, count=None): pass
    def close(self): pass

class MockHeaders(UserDict.UserDict):
    def getallmatchingheaders(self, name):
        r = []
        for k, v in self.data.items():
            if k.lower() == name:
                r.append("%s: %s" % (k, v))
        return r

class MockResponse(StringIO.StringIO):
    def __init__(self, code, msg, headers, data, url=None):
        StringIO.StringIO.__init__(self, data)
        self.code, self.msg, self.headers, self.url = code, msg, headers, url
    def info(self):
        return self.headers
    def geturl(self):
        return self.url

class MockCookieJar:
    def add_cookie_header(self, request, unverifiable=False):
        self.ach_req, self.ach_u = request, unverifiable
    def extract_cookies(self, response, request, unverifiable=False):
        self.ec_req, self.ec_r, self.ec_u = request, response, unverifiable

class MockMethod:
    def __init__(self, meth_name, action, handle):
        self.meth_name = meth_name
        self.handle = handle
        self.action = action
    def __call__(self, *args):
        return apply(self.handle, (self.meth_name, self.action)+args)

class MockHandler:
    processor_order = 500
    def __init__(self, methods):
        self._define_methods(methods)
    def _define_methods(self, methods):
        for spec in methods:
            if len(spec) == 2: name, action = spec
            else: name, action = spec, None
            meth = MockMethod(name, action, self.handle)
            setattr(self.__class__, name, meth)
    def handle(self, fn_name, action, *args, **kwds):
        self.parent.calls.append((self, fn_name, args, kwds))
        if action is None:
            return None
        elif action == "return self":
            return self
        elif action == "return response":
            res = MockResponse(200, "OK", {}, "")
            return res
        elif action == "return request":
            return Request("http://blah/")
        elif startswith(action, "error"):
            code = int(action[-3:])
            res = MockResponse(200, "OK", {}, "")
            return self.parent.error("http", args[0], res, code, "", {})
        elif action == "raise":
            raise urllib2.URLError("blah")
        assert False
    def close(self): pass
    def add_parent(self, parent):
        self.parent = parent
        self.parent.calls = []
    def __cmp__(self, other):
        if hasattr(other, "handler_order"):
            return cmp(self.handler_order, other.handler_order)
        # No handler_order, leave in original order.  Yuck.
        return -1
        #return cmp(id(self), id(other))


def add_ordered_mock_handlers(opener, meth_spec):
    handlers = []
    count = 0
    for meths in meth_spec:
        class MockHandlerSubclass(MockHandler): pass
        h = MockHandlerSubclass(meths)
        h.handler_order = h.processor_order = count
        h.add_parent(opener)
        count = count + 1
        handlers.append(h)
        opener.add_handler(h)
    return handlers

class OpenerDirectorTests(unittest.TestCase):

    def test_handled(self):
        # handler returning non-None means no more handlers will be called
        o = OpenerDirector()
        meth_spec = [
            ["http_open", "ftp_open", "http_error_302"],
            ["ftp_open"],
            [("http_open", "return self")],
            [("http_open", "return self")],
            ]
        handlers = add_ordered_mock_handlers(o, meth_spec)

        req = Request("http://example.com/")
        r = o.open(req)
        # Second http_open gets called, third doesn't, since second returned
        # non-None.  Handlers without http_open never get any methods called
        # on them.
        # In fact, second mock handler returns self (instead of response),
        # which becomes the OpenerDirector's return value.
        self.assert_(r == handlers[2])
        calls = [(handlers[0], "http_open"), (handlers[2], "http_open")]
        for i in range(len(o.calls)):
            handler, name, args, kwds = o.calls[i]
            self.assert_((handler, name) == calls[i])
            self.assert_(args == (req,))

    def test_handler_order(self):
        o = OpenerDirector()
        handlers = []
        for meths, handler_order in [
            ([("http_open", "return self")], 500),
            (["http_open"], 0),
            ]:
            class MockHandlerSubclass(MockHandler): pass
            h = MockHandlerSubclass(meths)
            h.handler_order = handler_order
            handlers.append(h)
            o.add_handler(h)

        r = o.open("http://example.com/")
        # handlers called in reverse order, thanks to their sort order
        self.assert_(o.calls[0][0] == handlers[1])
        self.assert_(o.calls[1][0] == handlers[0])

    def test_raise(self):
        # raising URLError stops processing of request
        o = OpenerDirector()
        meth_spec = [
            [("http_open", "raise")],
            [("http_open", "return self")],
            ]
        handlers = add_ordered_mock_handlers(o, meth_spec)

        req = Request("http://example.com/")
        self.assertRaises(urllib2.URLError, o.open, req)
        self.assert_(o.calls == [(handlers[0], "http_open", (req,), {})])

##     def test_error(self):
##         # XXX this doesn't actually seem to be used in standard library,
##         #  but should really be tested anyway...

    def test_http_error(self):
        # XXX http_error_default
        # http errors are a special case
        o = OpenerDirector()
        meth_spec = [
            [("http_open", "error 302")],
            [("http_error_400", "raise"), "http_open"],
            [("http_error_302", "return response"), "http_error_303",
             "http_error"],
            [("http_error_302")],
            ]
        handlers = add_ordered_mock_handlers(o, meth_spec)

        class Unknown: pass

        req = Request("http://example.com/")
        r = o.open(req)
        assert len(o.calls) == 2
        calls = [(handlers[0], "http_open", (req,)),
                 (handlers[2], "http_error_302", (req, Unknown, 302, "", {}))]
        for i in range(len(calls)):
            handler, method_name, args, kwds = o.calls[i]
            self.assert_((handler, method_name) == calls[i][:2])
            # check handler methods were called with expected arguments
            expected_args = calls[i][2]
            for j in range(len(args)):
                if expected_args[j] is not Unknown:
                    self.assert_(args[j] == expected_args[j])

    def test_processors(self):
        # *_request / *_response methods get called appropriately
        o = OpenerDirector()
        meth_spec = [
            [("http_request", "return request"),
             ("http_response", "return response")],
            [("http_request", "return request"),
             ("http_response", "return response")],
            ]
        handlers = add_ordered_mock_handlers(o, meth_spec)

        req = Request("http://example.com/")
        r = o.open(req)
        # processor methods are called on *all* handlers that define them,
        # not just the first handler
        calls = [(handlers[0], "http_request"), (handlers[1], "http_request"),
                 (handlers[0], "http_response"), (handlers[1], "http_response")]

        for i in range(len(o.calls)):
            handler, name, args, kwds = o.calls[i]
            if i < 2:
                # *_request
                self.assert_((handler, name) == calls[i])
                self.assert_(len(args) == 1)
                self.assert_(isinstance(args[0], Request))
            else:
                # *_response
                self.assert_((handler, name) == calls[i])
                self.assert_(len(args) == 2)
                self.assert_(isinstance(args[0], Request))
                # response from opener.open is None, because there's no
                # handler that defines http_open to handle it
                self.assert_(args[1] is None or
                             isinstance(args[1], MockResponse))


class MockHTTPResponse:
    def __init__(self, fp, msg, status, reason):
        self.fp = fp
        self.msg = msg
        self.status = status
        self.reason = reason
    def read(self):
        return ''

class MockHTTPClass:
    def __init__(self):
        self.req_headers = []
        self.data = None
        self.raise_on_endheaders = False
    def __call__(self, host):
        self.host = host
        return self
    def set_debuglevel(self, level):
        self.level = level
    def request(self, method, url, body=None, headers={}):
        self.method = method
        self.selector = url
        self.req_headers.extend(headers.items())
        if body:
            self.data = body
        if self.raise_on_endheaders:
            import socket
            raise socket.error()
    def getresponse(self):
        return MockHTTPResponse(MockFile(), {}, 200, "OK")

class MockFTPWrapper:
    def __init__(self, data): self.data = data
    def retrfile(self, filename, filetype):
        self.filename, self.filetype = filename, filetype
        return StringIO.StringIO(self.data), len(self.data)

class NullFTPHandler(urllib2.FTPHandler):
    def __init__(self, data): self.data = data
    def connect_ftp(self, user, passwd, host, port, dirs):
        self.user, self.passwd = user, passwd
        self.host, self.port = host, port
        self.dirs = dirs
        self.ftpwrapper = MockFTPWrapper(self.data)
        return self.ftpwrapper

def sanepathname2url(path):
    import urllib
    urlpath = urllib.pathname2url(path)
    if os.name == "nt" and urlpath.startswith("///"):
        urlpath = urlpath[2:]
    # XXX don't ask me about the mac...
    return urlpath

class MockRobotFileParserClass:
    def __init__(self):
        self.calls = []
        self._can_fetch = True
    def clear(self):
        self.calls = []
    def __call__(self):
        self.calls.append("__call__")
        return self
    def set_url(self, url):
        self.calls.append(("set_url", url))
    def read(self):
        self.calls.append("read")
    def can_fetch(self, ua, url):
        self.calls.append(("can_fetch", ua, url))
        return self._can_fetch

class HandlerTests(unittest.TestCase):

    if hasattr(sys, "version_info") and sys.version_info > (2, 1, 3, "final", 0):

        def test_ftp(self):
            import ftplib, socket
            data = "rheum rhaponicum"
            h = NullFTPHandler(data)
            o = h.parent = MockOpener()

            for url, host, port, type_, dirs, filename, mimetype in [
                ("ftp://localhost/foo/bar/baz.html",
                 "localhost", ftplib.FTP_PORT, "I",
                 ["foo", "bar"], "baz.html", "text/html"),
                # XXXX Bug: FTPHandler tries to gethostbyname "localhost:80",
                #  with the port still there.
                #("ftp://localhost:80/foo/bar/",
                # "localhost", 80, "D",
                # ["foo", "bar"], "", None),
                # XXXX bug: second use of splitattr() in FTPHandler should be
                #  splitvalue()
                #("ftp://localhost/baz.gif;type=a",
                # "localhost", ftplib.FTP_PORT, "A",
                # [], "baz.gif", "image/gif"),
                ]:
                r = h.ftp_open(Request(url))
                # ftp authentication not yet implemented by FTPHandler
                self.assert_(h.user == h.passwd == "")
                self.assert_(h.host == socket.gethostbyname(host))
                self.assert_(h.port == port)
                self.assert_(h.dirs == dirs)
                self.assert_(h.ftpwrapper.filename == filename)
                self.assert_(h.ftpwrapper.filetype == type_)
                headers = r.info()
                self.assert_(headers["Content-type"] == mimetype)
                self.assert_(int(headers["Content-length"]) == len(data))

        def test_file(self):
            import time, rfc822, socket
            h = urllib2.FileHandler()
            o = h.parent = MockOpener()

            #TESTFN = test_support.TESTFN
            TESTFN = "test.txt"
            urlpath = sanepathname2url(os.path.abspath(TESTFN))
            towrite = "hello, world\n"
            try:
                fqdn = socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                fqdn = "localhost"
            for url in [
                "file://localhost%s" % urlpath,
                "file://%s" % urlpath,
                "file://%s%s" % (socket.gethostbyname('localhost'), urlpath),
                "file://%s%s" % (fqdn, urlpath)
                ]:
                f = open(TESTFN, "wb")
                try:
                    try:
                        f.write(towrite)
                    finally:
                        f.close()

                    r = h.file_open(Request(url))
                    try:
                        data = r.read()
                        headers = r.info()
                        newurl = r.geturl()
                    finally:
                        r.close()
                    stats = os.stat(TESTFN)
                    modified = rfc822.formatdate(stats.st_mtime)
                finally:
                    os.remove(TESTFN)
                self.assertEqual(data, towrite)
                self.assertEqual(headers["Content-type"], "text/plain")
                self.assertEqual(headers["Content-length"], "13")
                self.assertEqual(headers["Last-modified"], modified)

            for url in [
                "file://localhost:80%s" % urlpath,
    # XXXX bug: these fail with socket.gaierror, should be URLError
    ##             "file://%s:80%s/%s" % (socket.gethostbyname('localhost'),
    ##                                    os.getcwd(), TESTFN),
    ##             "file://somerandomhost.ontheinternet.com%s/%s" %
    ##             (os.getcwd(), TESTFN),
                ]:
                try:
                    f = open(TESTFN, "wb")
                    try:
                        f.write(towrite)
                    finally:
                        f.close()

                    self.assertRaises(urllib2.URLError,
                                      h.file_open, Request(url))
                finally:
                    os.remove(TESTFN)

            h = urllib2.FileHandler()
            o = h.parent = MockOpener()
            # XXXX why does // mean ftp (and /// mean not ftp!), and where
            #  is file: scheme specified?  I think this is really a bug, and
            #  what was intended was to distinguish between URLs like:
            # file:/blah.txt (a file)
            # file://localhost/blah.txt (a file)
            # file:///blah.txt (a file)
            # file://ftp.example.com/blah.txt (an ftp URL)
            for url, ftp in [
                ("file://ftp.example.com//foo.txt", True),
                ("file://ftp.example.com///foo.txt", False),
    # XXXX bug: fails with OSError, should be URLError
                ("file://ftp.example.com/foo.txt", False),
                ]:
                req = Request(url)
                try:
                    h.file_open(req)
                # XXXX remove OSError when bug fixed
                except (urllib2.URLError, OSError):
                    self.assert_(not ftp)
                else:
                    self.assert_(o.req is req)
                    self.assertEqual(req.type, "ftp")

    def test_http(self):
        h = AbstractHTTPHandler()
        o = h.parent = MockOpener()

        url = "http://example.com/"
        for method, data in [("GET", None), ("POST", "blah")]:
            req = Request(url, data, {"Foo": "bar"})
            req.add_unredirected_header("Spam", "eggs")
            http = MockHTTPClass()
            r = h.do_open(http, req)

            # result attributes
            r.read; r.readline  # wrapped MockFile methods
            r.info; r.geturl  # addinfourl methods
            r.code, r.msg == 200, "OK"  # added from MockHTTPClass.getreply()
            hdrs = r.info()
            hdrs.get; hdrs.has_key  # r.info() gives dict from .getreply()
            self.assert_(r.geturl() == url)

            self.assert_(http.host == "example.com")
            self.assert_(http.level == 0)
            self.assert_(http.method == method)
            self.assert_(http.selector == "/")
            http.req_headers.sort()
            self.assert_(http.req_headers == [
                ("Connection", "close"),
                ("Foo", "bar"), ("Spam", "eggs")])
            self.assert_(http.data == data)

        # check socket.error converted to URLError
        http.raise_on_endheaders = True
        self.assertRaises(urllib2.URLError, h.do_open, http, req)

        # check adding of standard headers
        o.addheaders = [("Spam", "eggs")]
        for data in "", None:  # POST, GET
            req = Request("http://example.com/", data)
            r = MockResponse(200, "OK", {}, "")
            newreq = h.do_request_(req)
            if data is None:  # GET
                self.assert_(not req.unredirected_hdrs.has_key("Content-length"))
                self.assert_(not req.unredirected_hdrs.has_key("Content-type"))
            else:  # POST
                # No longer true, due to workarouhd for buggy httplib
                # in Python versions < 2.4:
                #self.assert_(req.unredirected_hdrs["Content-length"] == "0")
                self.assert_(req.unredirected_hdrs["Content-type"] ==
                             "application/x-www-form-urlencoded")
            # XXX the details of Host could be better tested
            self.assert_(req.unredirected_hdrs["Host"] == "example.com")
            self.assert_(req.unredirected_hdrs["Spam"] == "eggs")

            # don't clobber existing headers
            req.add_unredirected_header("Content-length", "foo")
            req.add_unredirected_header("Content-type", "bar")
            req.add_unredirected_header("Host", "baz")
            req.add_unredirected_header("Spam", "foo")
            newreq = h.do_request_(req)
            self.assert_(req.unredirected_hdrs["Content-length"] == "foo")
            self.assert_(req.unredirected_hdrs["Content-type"] == "bar")
            self.assert_(req.unredirected_hdrs["Host"] == "baz")
            self.assert_(req.unredirected_hdrs["Spam"] == "foo")

    def test_request_upgrade(self):
        new_req_class = hasattr(urllib2.Request, "has_header")

        h = HTTPRequestUpgradeProcessor()
        o = h.parent = MockOpener()

        # urllib2.Request gets upgraded, unless it's the new Request
        # class from 2.4
        req = urllib2.Request("http://example.com/")
        newreq = h.http_request(req)
        if new_req_class:
            self.assert_(newreq is req)
        else:
            self.assert_(newreq is not req)
        if new_req_class:
            self.assert_(newreq.__class__ is not Request)
        else:
            self.assert_(newreq.__class__ is Request)
        # ClientCookie._urllib2_support.Request doesn't get upgraded
        req = Request("http://example.com/")
        newreq = h.http_request(req)
        self.assert_(newreq is req)
        self.assert_(newreq.__class__ is Request)

    def test_referer(self):
        h = HTTPRefererProcessor()
        o = h.parent = MockOpener()

        # normal case
        url = "http://example.com/"
        req = Request(url)
        r = MockResponse(200, "OK", {}, "", url)
        newr = h.http_response(req, r)
        self.assert_(r is newr)
        self.assert_(h.referer == url)
        newreq = h.http_request(req)
        self.assert_(req is newreq)
        self.assert_(req.unredirected_hdrs["Referer"] == url)
        # don't clobber existing Referer
        ref = "http://set.by.user.com/"
        req.add_unredirected_header("Referer", ref)
        newreq = h.http_request(req)
        self.assert_(req is newreq)
        self.assert_(req.unredirected_hdrs["Referer"] == ref)

    def test_errors(self):
        h = HTTPErrorProcessor()
        o = h.parent = MockOpener()

        url = "http://example.com/"
        req = Request(url)
        # 200 OK is passed through
        r = MockResponse(200, "OK", {}, "", url)
        newr = h.http_response(req, r)
        self.assert_(r is newr)
        self.assert_(not hasattr(o, "proto"))  # o.error not called
        # anything else calls o.error (and MockOpener returns None, here)
        r = MockResponse(201, "Created", {}, "", url)
        self.assert_(h.http_response(req, r) is None)
        self.assert_(o.proto == "http")  # o.error called
        self.assert_(o.args == (req, r, 201, "Created", {}))

    def test_robots(self):
        # XXX useragent
        try:
            import robotparser
        except ImportError:
            return  # skip test
        else:
            from ClientCookie import HTTPRobotRulesProcessor
        rfpc = MockRobotFileParserClass()
        h = HTTPRobotRulesProcessor(rfpc)

        url = "http://example.com:80/foo/bar.html"
        req = Request(url)
        # first time: initialise and set up robots.txt parser before checking
        #  whether OK to fetch URL
        h.http_request(req)
        self.assert_(rfpc.calls == [
            "__call__",
            ("set_url", "http://example.com:80/robots.txt"),
            "read",
            ("can_fetch", "", url),
            ])
        # second time: just use existing parser
        rfpc.clear()
        req = Request(url)
        h.http_request(req)
        self.assert_(rfpc.calls == [
            ("can_fetch", "", url),
            ])
        # different URL on same server: same again
        rfpc.clear()
        url = "http://example.com:80/blah.html"
        req = Request(url)
        h.http_request(req)
        self.assert_(rfpc.calls == [
            ("can_fetch", "", url),
            ])
        # disallowed URL
        rfpc.clear()
        rfpc._can_fetch = False
        url = "http://example.com:80/rhubarb.html"
        req = Request(url)
        try:
            h.http_request(req)
        except urllib2.HTTPError, e:
            self.assert_(e.request == req)
            self.assert_(e.code == 403)
        # new host: reload robots.txt (even though the host and port are
        #  unchanged, we treat this as a new host because
        #  "example.com" != "example.com:80")
        rfpc.clear()
        rfpc._can_fetch = True
        url = "http://example.com/rhubarb.html"
        req = Request(url)
        h.http_request(req)
        self.assert_(rfpc.calls == [
            "__call__",
            ("set_url", "http://example.com/robots.txt"),
            "read",
            ("can_fetch", "", url),
            ])
        # https url -> should fetch robots.txt from https url too
        rfpc.clear()
        url = "https://example.org/rhubarb.html"
        req = Request(url)
        h.http_request(req)
        self.assert_(rfpc.calls == [
            "__call__",
            ("set_url", "https://example.org/robots.txt"),
            "read",
            ("can_fetch", "", url),
            ])

    def test_cookies(self):
        cj = MockCookieJar()
        h = HTTPCookieProcessor(cj)
        o = h.parent = MockOpener()

        req = Request("http://example.com/")
        r = MockResponse(200, "OK", {}, "")
        newreq = h.http_request(req)
        self.assert_(cj.ach_req is req is newreq)
        self.assert_(req.origin_req_host == "example.com")
        self.assert_(cj.ach_u == False)
        newr = h.http_response(req, r)
        self.assert_(cj.ec_req is req)
        self.assert_(cj.ec_r is r is newr)
        self.assert_(cj.ec_u == False)

    def test_seekable(self):
        h = SeekableProcessor()
        o = h.parent = MockOpener()

        req = urllib2.Request("http://example.com/")
        class MockUnseekableResponse:
            code = 200
            msg = "OK"
            def info(self): pass
            def geturl(self): return ""
        r = MockUnseekableResponse()
        newr = h.http_response(req, r)
        self.assert_(not hasattr(r, "seek"))
        self.assert_(hasattr(newr, "seek"))

    def test_http_equiv(self):
        h = HTTPEquivProcessor()
        o = h.parent = MockOpener()

        req = Request("http://example.com/")
        r = MockResponse(
            200, "OK",
            MockHeaders({"Foo": "Bar", "Content-type": "text/html"}),
            '<html><head>'
            '<meta http-equiv="Refresh" content="spam&amp;eggs">'
            '</head></html>'
            )
        newr = h.http_response(req, r)
        headers = newr.info()
        self.assert_(headers["Refresh"] == "spam&eggs")
        self.assert_(headers["Foo"] == "Bar")

    def test_refresh(self):
        # XXX test processor constructor optional args
        h = HTTPRefreshProcessor(max_time=None, honor_time=False)

        for val in ['0; url="http://example.com/foo/"', "2"]:
            o = h.parent = MockOpener()
            req = Request("http://example.com/")
            headers = MockHeaders({"refresh": val})
            r = MockResponse(200, "OK", headers, "")
            newr = h.http_response(req, r)
            self.assertEqual(o.proto, "http")
            self.assertEqual(o.args, (req, r, "refresh", "OK", headers))

    def test_redirect(self):
        from_url = "http://example.com/a.html"
        to_url = "http://example.com/b.html"
        h = HTTPRedirectHandler()
        o = h.parent = MockOpener()

        # ordinary redirect behaviour
        for code in 301, 302, 303, 307, "refresh":
            for data in None, "blah\nblah\n":
                method = getattr(h, "http_error_%s" % code)
                req = Request(from_url, data)
                req.add_header("Nonsense", "viking=withhold")
                req.add_unredirected_header("Spam", "spam")
                req.origin_req_host = "example.com"  # XXX
                try:
                    method(req, MockFile(), code, "Blah",
                           MockHeaders({"location": to_url}))
                except urllib2.HTTPError:
                    # 307 in response to POST requires user OK
                    self.assert_(code == 307 and data is not None)
                self.assert_(o.req.get_full_url() == to_url)
                try:
                    self.assert_(o.req.get_method() == "GET")
                except AttributeError:
                    self.assert_(not o.req.has_data())
                self.assert_(o.req.headers["Nonsense"] == "viking=withhold")
                self.assert_(not o.req.headers.has_key("Spam"))
                self.assert_(not o.req.unredirected_hdrs.has_key("Spam"))

        # loop detection
        def redirect(h, req, url=to_url):
            h.http_error_302(req, MockFile(), 302, "Blah",
                             MockHeaders({"location": url}))
        # Note that the *original* request shares the same record of
        # redirections with the sub-requests caused by the redirections.

        # detect infinite loop redirect of a URL to itself
        req = Request(from_url)
        req.origin_req_host = "example.com"
        count = 0
        try:
            while 1:
                redirect(h, req, "http://example.com/")
                count = count + 1
        except urllib2.HTTPError:
            # don't stop until max_repeats, because cookies may introduce state
            self.assert_(count == HTTPRedirectHandler.max_repeats)

        # detect endless non-repeating chain of redirects
        req = Request(from_url)
        req.origin_req_host = "example.com"
        count = 0
        try:
            while 1:
                redirect(h, req, "http://example.com/%d" % count)
                count = count + 1
        except urllib2.HTTPError:
            self.assert_(count == HTTPRedirectHandler.max_redirections)


class UnescapeTests(unittest.TestCase):

    def test_unescape_charref(self):
        from ClientCookie._urllib2_support import \
             unescape_charref, get_entitydefs
        mdash_utf8 = u"\u2014".encode("utf-8")
        for ref, codepoint, utf8, latin1 in [
            ("38", 38, u"&".encode("utf-8"), "&"),
            ("x2014", 0x2014, mdash_utf8, "&#x2014;"),
            ("8212", 8212, mdash_utf8, "&#8212;"),
            ]:
            self.assertEqual(unescape_charref(ref, None), unichr(codepoint))
            self.assertEqual(unescape_charref(ref, 'latin-1'), latin1)
            self.assertEqual(unescape_charref(ref, 'utf-8'), utf8)

    def test_get_entitydefs(self):
        from ClientCookie._urllib2_support import get_entitydefs
        ed = get_entitydefs()
        for name, codepoint in [
            ("amp", ord(u"&")),
            ("lt", ord(u"<")),
            ("gt", ord(u">")),
            ("mdash", 0x2014),
            ("spades", 0x2660),
            ]:
            self.assertEqual(ed[name], codepoint)

    def test_unescape(self):
        import htmlentitydefs
        from ClientCookie._urllib2_support import unescape, get_entitydefs
        data = "&amp; &lt; &mdash; &#8212; &#x2014;"
        mdash_utf8 = u"\u2014".encode("utf-8")
        ue = unescape(data, get_entitydefs(), "utf-8")
        self.assertEqual("& < %s %s %s" % ((mdash_utf8,)*3), ue)

        for text, expect in [
            ("&a&amp;", "&a&"),
            ("a&amp;", "a&"),
            ]:
            got = unescape(text, get_entitydefs(), "latin-1")
            self.assertEqual(got, expect)


class HeadParserTests(unittest.TestCase):

    def test(self):
        # XXX XHTML
        from ClientCookie import HeadParser
        htmls = [
            ("""<meta http-equiv="refresh" content="1; http://example.com/">
            """,
            [("refresh", "1; http://example.com/")]
            ),
            ("""
            <html><head>
            <meta http-equiv="refresh" content="1; http://example.com/">
            <meta name="spam" content="eggs">
            <meta http-equiv="foo" content="bar">
            <p> <!-- p is not allowed in head, so parsing should stop here-->
            <meta http-equiv="moo" content="cow">
            </html>
            """,
             [("refresh", "1; http://example.com/"), ("foo", "bar")])
            ]
        for html, result in htmls:
            self.assertEqual(parse_head(StringIO.StringIO(html), HeadParser()), result)


class MockHTTPHandler(HTTPHandler):
    def __init__(self): self._count = 0
    def http_open(self, req):
        import mimetools
        from StringIO import StringIO
        if self._count == 0:
            self._count = self._count + 1
            msg = mimetools.Message(
                StringIO("Location: http://www.cracker.com/\r\n\r\n"))
            return self.parent.error(
                "http", req, MockFile(), 302, "Found", msg)
        else:
            self.req = req
            msg = mimetools.Message(StringIO("\r\n\r\n"))
            return MockResponse(200, "OK", msg, "", req.get_full_url())

class MiscTests(unittest.TestCase):

    def test_cookie_redirect(self):
        # cookies shouldn't leak into redirected requests
        from ClientCookie import CookieJar, build_opener, HTTPHandler, \
             HTTPCookieProcessor
        from urllib2 import HTTPError

        from test_cookies import interact_netscape

        cj = CookieJar()
        interact_netscape(cj, "http://www.example.com/", "spam=eggs")
        hh = MockHTTPHandler()
        cp = HTTPCookieProcessor(cj)
        o = build_opener(hh, cp)
        o.open("http://www.example.com/")
        self.assert_(not hh.req.has_header("Cookie"))


class MyHTTPHandler(HTTPHandler): pass
class FooHandler(urllib2.BaseHandler):
    def foo_open(self): pass
class BarHandler(urllib2.BaseHandler):
    def bar_open(self): pass

class A:
    def a(self): pass
class B(A):
    def a(self): pass
    def b(self): pass
class C(A):
    def c(self): pass
class D(C, B):
    def a(self): pass
    def d(self): pass

class FunctionTests(unittest.TestCase):

    def test_build_opener(self):
        o = build_opener(FooHandler, BarHandler)
        self.opener_has_handler(o, FooHandler)
        self.opener_has_handler(o, BarHandler)

        # can take a mix of classes and instances
        o = build_opener(FooHandler, BarHandler())
        self.opener_has_handler(o, FooHandler)
        self.opener_has_handler(o, BarHandler)

        # subclasses of default handlers override default handlers
        o = build_opener(MyHTTPHandler)
        self.opener_has_handler(o, MyHTTPHandler)

        # a particular case of overriding: default handlers can be passed
        # in explicitly
        o = build_opener()
        self.opener_has_handler(o, HTTPHandler)
        o = build_opener(HTTPHandler)
        self.opener_has_handler(o, HTTPHandler)
        o = build_opener(HTTPHandler())
        self.opener_has_handler(o, HTTPHandler)

    def opener_has_handler(self, opener, handler_class):
        for h in opener.handlers:
            if h.__class__ == handler_class:
                break
        else:
            self.assert_(False)

    def _methnames(self, *objs):
        from ClientCookie._Opener import methnames
        r = []
        for i in range(len(objs)):
            obj = objs[i]
            names = methnames(obj)
            names.sort()
            # special methods vary over Python versions
            names = filter(lambda mn: mn[0:2] != "__" , names)
            r.append(names)
        return r

    def test_methnames(self):
        a, b, c, d = A(), B(), C(), D()
        a, b, c, d = self._methnames(a, b, c, d)
        self.assert_(a == ["a"])
        self.assert_(b == ["a", "b"])
        self.assert_(c == ["a", "c"])
        self.assert_(d == ["a", "b", "c", "d"])

        a, b, c, d = A(), B(), C(), D()
        a.x = lambda self: None
        b.y = lambda self: None
        d.z = lambda self: None
        a, b, c, d = self._methnames(a, b, c, d)
        self.assert_(a == ["a", "x"])
        self.assert_(b == ["a", "b", "y"])
        self.assert_(c == ["a", "c"])
        self.assert_(d == ["a", "b", "c", "d", "z"])


if __name__ == "__main__":
    unittest.main()
