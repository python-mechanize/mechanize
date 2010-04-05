#!/usr/bin/env python
"""Tests for mechanize.Browser."""

import StringIO
from unittest import TestCase
import re

import mechanize
from mechanize._response import test_html_response
FACTORY_CLASSES = [mechanize.DefaultFactory, mechanize.RobustFactory]


# XXX these 'mock' classes are badly in need of simplification / removal
# (note this stuff is also used by test_useragent.py and test_browser.doctest)
class MockMethod:
    def __init__(self, meth_name, action, handle):
        self.meth_name = meth_name
        self.handle = handle
        self.action = action
    def __call__(self, *args):
        return apply(self.handle, (self.meth_name, self.action)+args)

class MockHeaders(dict):
    def getheaders(self, name):
        name = name.lower()
        return [v for k, v in self.iteritems() if name == k.lower()]

class MockResponse:
    closeable_response = None
    def __init__(self, url="http://example.com/", data=None, info=None):
        self.url = url
        self.fp = StringIO.StringIO(data)
        if info is None: info = {}
        self._info = MockHeaders(info)
    def info(self): return self._info
    def geturl(self): return self.url
    def read(self, size=-1): return self.fp.read(size)
    def seek(self, whence):
        assert whence == 0
        self.fp.seek(0)
    def close(self): pass
    def get_data(self): pass

def make_mock_handler(response_class=MockResponse):
    class MockHandler:
        processor_order = 500
        handler_order = -1
        def __init__(self, methods):
            self._define_methods(methods)
        def _define_methods(self, methods):
            for name, action in methods:
                if name.endswith("_open"):
                    meth = MockMethod(name, action, self.handle)
                else:
                    meth = MockMethod(name, action, self.process)
                setattr(self.__class__, name, meth)
        def handle(self, fn_name, response, *args, **kwds):
            self.parent.calls.append((self, fn_name, args, kwds))
            if response:
                if isinstance(response, mechanize.HTTPError):
                    raise response
                r = response
                r.seek(0)
            else:
                r = response_class()
            req = args[0]
            r.url = req.get_full_url()
            return r
        def process(self, fn_name, action, *args, **kwds):
            self.parent.calls.append((self, fn_name, args, kwds))
            if fn_name.endswith("_request"):
                return args[0]
            else:
                return args[1]
        def close(self): pass
        def add_parent(self, parent):
            self.parent = parent
            self.parent.calls = []
        def __lt__(self, other):
            if not hasattr(other, "handler_order"):
                # Try to preserve the old behavior of having custom classes
                # inserted after default ones (works only for custom user
                # classes which are not aware of handler_order).
                return True
            return self.handler_order < other.handler_order
    return MockHandler

class TestBrowser(mechanize.Browser):
    default_features = []
    default_others = []
    default_schemes = []

class TestBrowser2(mechanize.Browser):
    # XXX better name!
    # As TestBrowser, this is neutered so doesn't know about protocol handling,
    # but still knows what to do with unknown schemes, etc., because
    # UserAgent's default_others list is left intact, including classes like
    # UnknownHandler
    default_features = []
    default_schemes = []


class BrowserTests(TestCase):

    def test_referer(self):
        b = TestBrowser()
        url = "http://www.example.com/"
        r = MockResponse(url,
"""<html>
<head><title>Title</title></head>
<body>
<form name="form1">
 <input type="hidden" name="foo" value="bar"></input>
 <input type="submit"></input>
 </form>
<a href="http://example.com/foo/bar.html" name="apples"></a>
<a href="https://example.com/spam/eggs.html" name="secure"></a>
<a href="blah://example.com/" name="pears"></a>
</body>
</html>
""", {"content-type": "text/html"})
        b.add_handler(make_mock_handler()([("http_open", r)]))

        # Referer not added by .open()...
        req = mechanize.Request(url)
        b.open(req)
        self.assert_(req.get_header("Referer") is None)
        # ...even if we're visiting a document
        b.open(req)
        self.assert_(req.get_header("Referer") is None)
        # Referer added by .click_link() and .click()
        b.select_form("form1")
        req2 = b.click()
        self.assertEqual(req2.get_header("Referer"), url)
        r2 = b.open(req2)
        req3 = b.click_link(name="apples")
        self.assertEqual(req3.get_header("Referer"), url+"?foo=bar")
        # Referer not added when going from https to http URL
        b.add_handler(make_mock_handler()([("https_open", r)]))
        r3 = b.open(req3)
        req4 = b.click_link(name="secure")
        self.assertEqual(req4.get_header("Referer"),
                         "http://example.com/foo/bar.html")
        r4 = b.open(req4)
        req5 = b.click_link(name="apples")
        self.assert_(not req5.has_header("Referer"))
        # Referer not added for non-http, non-https requests
        b.add_handler(make_mock_handler()([("blah_open", r)]))
        req6 = b.click_link(name="pears")
        self.assert_(not req6.has_header("Referer"))
        # Referer not added when going from non-http, non-https URL
        r4 = b.open(req6)
        req7 = b.click_link(name="apples")
        self.assert_(not req7.has_header("Referer"))

        # XXX Referer added for redirect

    def test_encoding(self):
        import mechanize
        from StringIO import StringIO
        import urllib, mimetools
        # always take first encoding, since that's the one from the real HTTP
        # headers, rather than from HTTP-EQUIV
        b = mechanize.Browser()
        for s, ct in [("", mechanize._html.DEFAULT_ENCODING),

                      ("Foo: Bar\r\n\r\n", mechanize._html.DEFAULT_ENCODING),

                      ("Content-Type: text/html; charset=UTF-8\r\n\r\n",
                       "UTF-8"),

                      ("Content-Type: text/html; charset=UTF-8\r\n"
                       "Content-Type: text/html; charset=KOI8-R\r\n\r\n",
                       "UTF-8"),
                      ]:
            msg = mimetools.Message(StringIO(s))
            r = urllib.addinfourl(StringIO(""), msg, "http://www.example.com/")
            b.set_response(r)
            self.assertEqual(b.encoding(), ct)

    def test_history(self):
        import mechanize
        from mechanize import _response

        def same_response(ra, rb):
            return ra.wrapped is rb.wrapped

        class Handler(mechanize.BaseHandler):
            def http_open(self, request):
                r = _response.test_response(url=request.get_full_url())
                # these tests aren't interested in auto-.reload() behaviour of
                # .back(), so read the response to prevent that happening
                r.get_data()
                return r

        b = TestBrowser2()
        b.add_handler(Handler())
        self.assertRaises(mechanize.BrowserStateError, b.back)
        r1 = b.open("http://example.com/")
        self.assertRaises(mechanize.BrowserStateError, b.back)
        r2 = b.open("http://example.com/foo")
        self.assert_(same_response(b.back(), r1))
        r3 = b.open("http://example.com/bar")
        r4 = b.open("http://example.com/spam")
        self.assert_(same_response(b.back(), r3))
        self.assert_(same_response(b.back(), r1))
        self.assertEquals(b.geturl(), "http://example.com/")
        self.assertRaises(mechanize.BrowserStateError, b.back)
        # reloading does a real HTTP fetch rather than using history cache
        r5 = b.reload()
        self.assert_(not same_response(r5, r1))
        # .geturl() gets fed through to b.response
        self.assertEquals(b.geturl(), "http://example.com/")
        # can go back n times
        r6 = b.open("spam")
        self.assertEquals(b.geturl(), "http://example.com/spam")
        r7 = b.open("/spam")
        self.assert_(same_response(b.response(), r7))
        self.assertEquals(b.geturl(), "http://example.com/spam")
        self.assert_(same_response(b.back(2), r5))
        self.assertEquals(b.geturl(), "http://example.com/")
        self.assertRaises(mechanize.BrowserStateError, b.back, 2)
        r8 = b.open("/spam")

        # even if we get an HTTPError, history, .response() and .request should
        # still get updated
        class Handler2(mechanize.BaseHandler):
            def https_open(self, request):
                r = mechanize.HTTPError(
                    "https://example.com/bad", 503, "Oops",
                    MockHeaders(), StringIO.StringIO())
                return r
        b.add_handler(Handler2())
        self.assertRaises(mechanize.HTTPError, b.open,
                          "https://example.com/badreq")
        self.assertEqual(b.response().geturl(), "https://example.com/bad")
        self.assertEqual(b.request.get_full_url(),
                         "https://example.com/badreq")
        self.assert_(same_response(b.back(), r8))

        # .close() should make use of Browser methods and attributes complain
        # noisily, since they should not be called after .close()
        b.form = "blah"
        b.close()
        for attr in ("form open error retrieve add_handler "
                     "request response set_response geturl reload back "
                     "clear_history set_cookie links forms viewing_html "
                     "encoding title select_form click submit click_link "
                     "follow_link find_link".split()
                     ):
            self.assert_(getattr(b, attr) is None)

    def test_reload_read_incomplete(self):
        import mechanize
        from mechanize._response import test_response
        class Browser(TestBrowser):
            def __init__(self):
                TestBrowser.__init__(self)
                self.reloaded = False
            def reload(self):
                self.reloaded = True
                TestBrowser.reload(self)
        br = Browser()
        data = "<html><head><title></title></head><body>%s</body></html>"
        data = data % ("The quick brown fox jumps over the lazy dog."*100)
        class Handler(mechanize.BaseHandler):
            def http_open(self, requst):
                return test_response(data, [("content-type", "text/html")])
        br.add_handler(Handler())

        # .reload() on .back() if the whole response hasn't already been read
        # (.read_incomplete is True)
        r = br.open("http://example.com")
        r.read(10)
        br.open('http://www.example.com/blah')
        self.failIf(br.reloaded)
        br.back()
        self.assert_(br.reloaded)

        # don't reload if already read
        br.reloaded = False
        br.response().read()
        br.open('http://www.example.com/blah')
        br.back()
        self.failIf(br.reloaded)

    def test_viewing_html(self):
        # XXX not testing multiple Content-Type headers
        import mechanize
        url = "http://example.com/"

        for allow_xhtml in False, True:
            for ct, expect in [
                (None, False),
                ("text/plain", False),
                ("text/html", True),

                # don't try to handle XML until we can do it right!
                ("text/xhtml", allow_xhtml),
                ("text/xml", allow_xhtml),
                ("application/xml", allow_xhtml),
                ("application/xhtml+xml", allow_xhtml),

                ("text/html; charset=blah", True),
                (" text/html ; charset=ook ", True),
                ]:
                b = TestBrowser(mechanize.DefaultFactory(
                    i_want_broken_xhtml_support=allow_xhtml))
                hdrs = {}
                if ct is not None:
                    hdrs["Content-Type"] = ct
                b.add_handler(make_mock_handler()([("http_open",
                                            MockResponse(url, "", hdrs))]))
                b.open(url)
                self.assertEqual(b.viewing_html(), expect)

        for allow_xhtml in False, True:
            for ext, expect in [
                (".htm", True),
                (".html", True),

                # don't try to handle XML until we can do it right!
                (".xhtml", allow_xhtml),

                (".html?foo=bar&a=b;whelk#kool", True),
                (".txt", False),
                (".xml", False),
                ("", False),
                ]:
                b = TestBrowser(mechanize.DefaultFactory(
                    i_want_broken_xhtml_support=allow_xhtml))
                url = "http://example.com/foo"+ext
                b.add_handler(make_mock_handler()(
                    [("http_open", MockResponse(url, "", {}))]))
                b.open(url)
                self.assertEqual(b.viewing_html(), expect)

    def test_empty(self):
        for factory_class in FACTORY_CLASSES:
            self._test_empty(factory_class())

    def _test_empty(self, factory):
        import mechanize
        url = "http://example.com/"

        b = TestBrowser(factory=factory)

        self.assert_(b.response() is None)

        # To open a relative reference (often called a "relative URL"), you
        # have to have already opened a URL for it "to be relative to".
        self.assertRaises(mechanize.BrowserStateError, b.open, "relative_ref")

        # we can still clear the history even if we've not visited any URL
        b.clear_history()

        # most methods raise BrowserStateError...
        def test_state_error(method_names):
            for attr in method_names:
                method = getattr(b, attr)
                #print attr
                self.assertRaises(mechanize.BrowserStateError, method)
            self.assertRaises(mechanize.BrowserStateError, b.select_form,
                              name="blah")
            self.assertRaises(mechanize.BrowserStateError, b.find_link,
                              name="blah")
        # ...if not visiting a URL...
        test_state_error(("geturl reload back viewing_html encoding "
                          "click links forms title select_form".split()))
        self.assertRaises(mechanize.BrowserStateError, b.set_cookie, "foo=bar")
        self.assertRaises(mechanize.BrowserStateError, b.submit, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.click_link, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.follow_link, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.find_link, nr=0)
        # ...and lots do so if visiting a non-HTML URL
        b.add_handler(make_mock_handler()(
            [("http_open", MockResponse(url, "", {}))]))
        r = b.open(url)
        self.assert_(not b.viewing_html())
        test_state_error("click links forms title select_form".split())
        self.assertRaises(mechanize.BrowserStateError, b.submit, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.click_link, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.follow_link, nr=0)
        self.assertRaises(mechanize.BrowserStateError, b.find_link, nr=0)

        b = TestBrowser()
        r = MockResponse(url,
"""<html>
<head><title>Title</title></head>
<body>
</body>
</html>
""", {"content-type": "text/html"})
        b.add_handler(make_mock_handler()([("http_open", r)]))
        r = b.open(url)
        self.assertEqual(b.title(), "Title")
        self.assertEqual(len(list(b.links())), 0)
        self.assertEqual(len(list(b.forms())), 0)
        self.assertRaises(ValueError, b.select_form)
        self.assertRaises(mechanize.FormNotFoundError, b.select_form,
                          name="blah")
        self.assertRaises(mechanize.FormNotFoundError, b.select_form,
                          predicate=lambda form: form is not b.global_form())
        self.assertRaises(mechanize.LinkNotFoundError, b.find_link,
                          name="blah")
        self.assertRaises(mechanize.LinkNotFoundError, b.find_link,
                          predicate=lambda x: True)

    def test_forms(self):
        for factory_class in FACTORY_CLASSES:
            self._test_forms(factory_class())
    def _test_forms(self, factory):
        import mechanize
        url = "http://example.com"

        b = TestBrowser(factory=factory)
        r = test_html_response(
            url=url,
            headers=[("content-type", "text/html")],
            data="""\
<html>
<head><title>Title</title></head>
<body>
<form name="form1">
 <input type="text"></input>
 <input type="checkbox" name="cheeses" value="cheddar"></input>
 <input type="checkbox" name="cheeses" value="edam"></input>
 <input type="submit" name="one"></input>
</form>
<a href="http://example.com/foo/bar.html" name="apples">
<form name="form2">
 <input type="submit" name="two">
</form>
</body>
</html>
"""
            )
        b.add_handler(make_mock_handler()([("http_open", r)]))
        r = b.open(url)

        forms = list(b.forms())
        self.assertEqual(len(forms), 2)
        for got, expect in zip([f.name for f in forms], [
            "form1", "form2"]):
            self.assertEqual(got, expect)

        self.assertRaises(mechanize.FormNotFoundError, b.select_form, "foo")

        # no form is set yet
        self.assertRaises(AttributeError, getattr, b, "possible_items")
        b.select_form("form1")
        # now unknown methods are fed through to selected mechanize.HTMLForm
        self.assertEqual(
            [i.name for i in b.find_control("cheeses").items],
            ["cheddar", "edam"])
        b["cheeses"] = ["cheddar", "edam"]
        self.assertEqual(b.click_pairs(), [
            ("cheeses", "cheddar"), ("cheeses", "edam"), ("one", "")])

        b.select_form(nr=1)
        self.assertEqual(b.name, "form2")
        self.assertEqual(b.click_pairs(), [("two", "")])

    def test_link_encoding(self):
        for factory_class in FACTORY_CLASSES:
            self._test_link_encoding(factory_class())
    def _test_link_encoding(self, factory):
        import mechanize
        from mechanize._rfc3986 import clean_url
        url = "http://example.com/"
        for encoding in ["UTF-8", "latin-1"]:
            encoding_decl = "; charset=%s" % encoding
            b = TestBrowser(factory=factory)
            r = MockResponse(url, """\
<a href="http://example.com/foo/bar&mdash;&#x2014;.html"
   name="name0&mdash;&#x2014;">blah&mdash;&#x2014;</a>
""", #"
{"content-type": "text/html%s" % encoding_decl})
            b.add_handler(make_mock_handler()([("http_open", r)]))
            r = b.open(url)

            Link = mechanize.Link
            try:
                mdashx2 = u"\u2014".encode(encoding)*2
            except UnicodeError:
                mdashx2 = '&mdash;&#x2014;'
            qmdashx2 = clean_url(mdashx2, encoding)
            # base_url, url, text, tag, attrs
            exp = Link(url, "http://example.com/foo/bar%s.html" % qmdashx2,
                       "blah"+mdashx2, "a",
                       [("href", "http://example.com/foo/bar%s.html" % mdashx2),
                        ("name", "name0%s" % mdashx2)])
            # nr
            link = b.find_link()
##             print
##             print exp
##             print link
            self.assertEqual(link, exp)

    def test_link_whitespace(self):
        from mechanize import Link
        for factory_class in FACTORY_CLASSES:
            base_url = "http://example.com/"
            url = "  http://example.com/foo.html%20+ "
            stripped_url = url.strip()
            html = '<a href="%s"></a>' % url
            b = TestBrowser(factory=factory_class())
            r = MockResponse(base_url, html, {"content-type": "text/html"})
            b.add_handler(make_mock_handler()([("http_open", r)]))
            r = b.open(base_url)
            link = b.find_link(nr=0)
            self.assertEqual(
                link,
                Link(base_url, stripped_url, "", "a", [("href", url)])
                )

    def test_links(self):
        for factory_class in FACTORY_CLASSES:
            self._test_links(factory_class())
    def _test_links(self, factory):
        import mechanize
        from mechanize import Link
        url = "http://example.com/"

        b = TestBrowser(factory=factory)
        r = MockResponse(url,
"""<html>
<head><title>Title</title></head>
<body>
<a href="http://example.com/foo/bar.html" name="apples"></a>
<a name="pears"></a>
<a href="spam" name="pears"></a>
<area href="blah" name="foo"></area>
<form name="form2">
 <input type="submit" name="two">
</form>
<frame name="name" href="href" src="src"></frame>
<iframe name="name2" href="href" src="src"></iframe>
<a name="name3" href="one">yada yada</a>
<a name="pears" href="two" weird="stuff">rhubarb</a>
<a></a>
<iframe src="foo"></iframe>
</body>
</html>
""", {"content-type": "text/html"})
        b.add_handler(make_mock_handler()([("http_open", r)]))
        r = b.open(url)

        exp_links = [
            # base_url, url, text, tag, attrs
            Link(url, "http://example.com/foo/bar.html", "", "a",
                 [("href", "http://example.com/foo/bar.html"),
                  ("name", "apples")]),
            Link(url, "spam", "", "a", [("href", "spam"), ("name", "pears")]),
            Link(url, "blah", None, "area",
                 [("href", "blah"), ("name", "foo")]),
            Link(url, "src", None, "frame",
                 [("name", "name"), ("href", "href"), ("src", "src")]),
            Link(url, "src", None, "iframe",
                 [("name", "name2"), ("href", "href"), ("src", "src")]),
            Link(url, "one", "yada yada", "a",
                 [("name", "name3"), ("href", "one")]),
            Link(url, "two", "rhubarb", "a",
                 [("name", "pears"), ("href", "two"), ("weird", "stuff")]),
            Link(url, "foo", None, "iframe",
                 [("src", "foo")]),
            ]
        links = list(b.links())
        self.assertEqual(len(links), len(exp_links))
        for got, expect in zip(links, exp_links):
            self.assertEqual(got, expect)
        # nr
        l = b.find_link()
        self.assertEqual(l.url, "http://example.com/foo/bar.html")
        l = b.find_link(nr=1)
        self.assertEqual(l.url, "spam")
        # text
        l = b.find_link(text="yada yada")
        self.assertEqual(l.url, "one")
        self.assertRaises(mechanize.LinkNotFoundError,
                          b.find_link, text="da ya")
        l = b.find_link(text_regex=re.compile("da ya"))
        self.assertEqual(l.url, "one")
        l = b.find_link(text_regex="da ya")
        self.assertEqual(l.url, "one")
        # name
        l = b.find_link(name="name3")
        self.assertEqual(l.url, "one")
        l = b.find_link(name_regex=re.compile("oo"))
        self.assertEqual(l.url, "blah")
        l = b.find_link(name_regex="oo")
        self.assertEqual(l.url, "blah")
        # url
        l = b.find_link(url="spam")
        self.assertEqual(l.url, "spam")
        l = b.find_link(url_regex=re.compile("pam"))
        self.assertEqual(l.url, "spam")
        l = b.find_link(url_regex="pam")
        self.assertEqual(l.url, "spam")
        # tag
        l = b.find_link(tag="area")
        self.assertEqual(l.url, "blah")
        # predicate
        l = b.find_link(predicate=
                        lambda l: dict(l.attrs).get("weird") == "stuff")
        self.assertEqual(l.url, "two")
        # combinations
        l = b.find_link(name="pears", nr=1)
        self.assertEqual(l.text, "rhubarb")
        l = b.find_link(url="src", nr=0, name="name2")
        self.assertEqual(l.tag, "iframe")
        self.assertEqual(l.url, "src")
        self.assertRaises(mechanize.LinkNotFoundError, b.find_link,
                          url="src", nr=1, name="name2")
        l = b.find_link(tag="a", predicate=
                        lambda l: dict(l.attrs).get("weird") == "stuff")
        self.assertEqual(l.url, "two")

        # .links()
        self.assertEqual(list(b.links(url="src")), [
            Link(url, url="src", text=None, tag="frame",
                 attrs=[("name", "name"), ("href", "href"), ("src", "src")]),
            Link(url, url="src", text=None, tag="iframe",
                 attrs=[("name", "name2"), ("href", "href"), ("src", "src")]),
            ])

    def test_base_uri(self):
        url = "http://example.com/"

        for html, urls in [
            (
"""<base href="http://www.python.org/foo/">
<a href="bar/baz.html"></a>
<a href="/bar/baz.html"></a>
<a href="http://example.com/bar %2f%2Fblah;/baz@~._-.html"></a>
""",
            [
            "http://www.python.org/foo/bar/baz.html",
            "http://www.python.org/bar/baz.html",
            "http://example.com/bar%20%2f%2Fblah;/baz@~._-.html",
            ]),
            (
"""<a href="bar/baz.html"></a>
<a href="/bar/baz.html"></a>
<a href="http://example.com/bar/baz.html"></a>
""",
            [
            "http://example.com/bar/baz.html",
            "http://example.com/bar/baz.html",
            "http://example.com/bar/baz.html",
            ]
            ),
            ]:
            b = TestBrowser()
            r = MockResponse(url, html, {"content-type": "text/html"})
            b.add_handler(make_mock_handler()([("http_open", r)]))
            r = b.open(url)
            self.assertEqual([link.absolute_url for link in b.links()], urls)

    def test_set_cookie(self):
        class CookieTestBrowser(TestBrowser):
            default_features = list(TestBrowser.default_features)+["_cookies"]

        # have to be visiting HTTP/HTTPS URL
        url = "ftp://example.com/"
        br = CookieTestBrowser()
        r = mechanize.make_response(
            "<html><head><title>Title</title></head><body></body></html>",
            [("content-type", "text/html")],
            url,
            200, "OK",
            )
        br.add_handler(make_mock_handler()([("http_open", r)]))
        handler = br._ua_handlers["_cookies"]
        cj = handler.cookiejar
        self.assertRaises(mechanize.BrowserStateError,
                          br.set_cookie, "foo=bar")
        self.assertEqual(len(cj), 0)


        url = "http://example.com/"
        br = CookieTestBrowser()
        r = mechanize.make_response(
            "<html><head><title>Title</title></head><body></body></html>",
            [("content-type", "text/html")],
            url,
            200, "OK",
            )
        br.add_handler(make_mock_handler()([("http_open", r)]))
        handler = br._ua_handlers["_cookies"]
        cj = handler.cookiejar

        # have to be visiting a URL
        self.assertRaises(mechanize.BrowserStateError,
                          br.set_cookie, "foo=bar")
        self.assertEqual(len(cj), 0)


        # normal case
        br.open(url)
        br.set_cookie("foo=bar")
        self.assertEqual(len(cj), 1)
        self.assertEqual(cj._cookies["example.com"]["/"]["foo"].value, "bar")


class ResponseTests(TestCase):

    def test_set_response(self):
        import copy
        from mechanize import response_seek_wrapper

        br = TestBrowser()
        url = "http://example.com/"
        html = """<html><body><a href="spam">click me</a></body></html>"""
        headers = {"content-type": "text/html"}
        r = response_seek_wrapper(MockResponse(url, html, headers))
        br.add_handler(make_mock_handler()([("http_open", r)]))

        r = br.open(url)
        self.assertEqual(r.read(), html)
        r.seek(0)
        self.assertEqual(copy.copy(r).read(), html)
        self.assertEqual(list(br.links())[0].url, "spam")

        newhtml = """<html><body><a href="eggs">click me</a></body></html>"""

        r.set_data(newhtml)
        self.assertEqual(r.read(), newhtml)
        self.assertEqual(br.response().read(), html)
        br.response().set_data(newhtml)
        self.assertEqual(br.response().read(), html)
        self.assertEqual(list(br.links())[0].url, "spam")
        r.seek(0)

        br.set_response(r)
        self.assertEqual(br.response().read(), newhtml)
        self.assertEqual(list(br.links())[0].url, "eggs")

    def test_str(self):
        import mimetools
        from mechanize import _response

        br = TestBrowser()
        self.assertEqual(
            str(br),
            "<TestBrowser (not visiting a URL)>"
            )

        fp = StringIO.StringIO('<html><form name="f"><input /></form></html>')
        headers = mimetools.Message(
            StringIO.StringIO("Content-type: text/html"))
        response = _response.response_seek_wrapper(
            _response.closeable_response(
            fp, headers, "http://example.com/", 200, "OK"))
        br.set_response(response)
        self.assertEqual(
            str(br),
            "<TestBrowser visiting http://example.com/>"
            )

        br.select_form(nr=0)
        self.assertEqual(
            str(br),
            """\
<TestBrowser visiting http://example.com/
 selected form:
 <f GET http://example.com/ application/x-www-form-urlencoded
  <TextControl(<None>=)>>
>""")


if __name__ == "__main__":
    import unittest
    unittest.main()
