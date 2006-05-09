#!/usr/bin/env python

import sys, random
from unittest import TestCase
import StringIO, re, UserDict, urllib2

import mechanize
FACTORY_CLASSES = [mechanize.DefaultFactory]
try:
    import BeautifulSoup
except ImportError:
    import warnings
    warnings.warn("skipping tests involving BeautifulSoup")
else:
    FACTORY_CLASSES.append(mechanize.RobustFactory)


def test_password_manager(self):
    """
    >>> mgr = mechanize.HTTPProxyPasswordMgr()
    >>> add = mgr.add_password

    >>> add("Some Realm", "http://example.com/", "joe", "password")
    >>> add("Some Realm", "http://example.com/ni", "ni", "ni")
    >>> add("c", "http://example.com/foo", "foo", "ni")
    >>> add("c", "http://example.com/bar", "bar", "nini")
    >>> add("b", "http://example.com/", "first", "blah")
    >>> add("b", "http://example.com/", "second", "spam")
    >>> add("a", "http://example.com", "1", "a")
    >>> add("Some Realm", "http://c.example.com:3128", "3", "c")
    >>> add("Some Realm", "d.example.com", "4", "d")
    >>> add("Some Realm", "e.example.com:3128", "5", "e")

    >>> mgr.find_user_password("Some Realm", "example.com")
    ('joe', 'password')
    >>> mgr.find_user_password("Some Realm", "http://example.com")
    ('joe', 'password')
    >>> mgr.find_user_password("Some Realm", "http://example.com/")
    ('joe', 'password')
    >>> mgr.find_user_password("Some Realm", "http://example.com/spam")
    ('joe', 'password')
    >>> mgr.find_user_password("Some Realm", "http://example.com/spam/spam")
    ('joe', 'password')
    >>> mgr.find_user_password("c", "http://example.com/foo")
    ('foo', 'ni')
    >>> mgr.find_user_password("c", "http://example.com/bar")
    ('bar', 'nini')

    Currently, we use the highest-level path where more than one match:

    >>> mgr.find_user_password("Some Realm", "http://example.com/ni")
    ('joe', 'password')

    Use latest add_password() in case of conflict:

    >>> mgr.find_user_password("b", "http://example.com/")
    ('second', 'spam')

    No special relationship between a.example.com and example.com:

    >>> mgr.find_user_password("a", "http://example.com/")
    ('1', 'a')
    >>> mgr.find_user_password("a", "http://a.example.com/")
    (None, None)

    Ports:

    >>> mgr.find_user_password("Some Realm", "c.example.com")
    (None, None)
    >>> mgr.find_user_password("Some Realm", "c.example.com:3128")
    ('3', 'c')
    >>> mgr.find_user_password("Some Realm", "http://c.example.com:3128")
    ('3', 'c')
    >>> mgr.find_user_password("Some Realm", "d.example.com")
    ('4', 'd')
    >>> mgr.find_user_password("Some Realm", "e.example.com:3128")
    ('5', 'e')


    Now features specific to HTTPProxyPasswordMgr.

    Default realm:

    >>> mgr.find_user_password("d", "f.example.com")
    (None, None)
    >>> add(None, "f.example.com", "6", "f")
    >>> mgr.find_user_password("d", "f.example.com")
    ('6', 'f')

    Default host/port:

    >>> mgr.find_user_password("e", "g.example.com")
    (None, None)
    >>> add("e", None, "7", "g")
    >>> mgr.find_user_password("e", "g.example.com")
    ('7', 'g')

    Default realm and host/port:

    >>> mgr.find_user_password("f", "h.example.com")
    (None, None)
    >>> add(None, None, "8", "h")
    >>> mgr.find_user_password("f", "h.example.com")
    ('8', 'h')

    Default realm beats default host/port:

    >>> add("d", None, "9", "i")
    >>> mgr.find_user_password("d", "f.example.com")
    ('6', 'f')

    """
    pass


class CachingGeneratorFunctionTests(TestCase):

    def _get_simple_cgenf(self, log):
        from mechanize._html import CachingGeneratorFunction
        todo = []
        for ii in range(2):
            def work(ii=ii):
                log.append(ii)
                return ii
            todo.append(work)
        def genf():
            for a in todo:
                yield a()
        return CachingGeneratorFunction(genf())

    def test_cache(self):
        log = []
        cgenf = self._get_simple_cgenf(log)
        for repeat in range(2):
            for ii, jj in zip(cgenf(), range(2)):
                self.assertEqual(ii, jj)
            self.assertEqual(log, range(2))  # work only done once

    def test_interleaved(self):
        log = []
        cgenf = self._get_simple_cgenf(log)
        cgen = cgenf()
        self.assertEqual(cgen.next(), 0)
        self.assertEqual(log, [0])
        cgen2 = cgenf()
        self.assertEqual(cgen2.next(), 0)
        self.assertEqual(log, [0])
        self.assertEqual(cgen.next(), 1)
        self.assertEqual(log, [0, 1])
        self.assertEqual(cgen2.next(), 1)
        self.assertEqual(log, [0, 1])
        self.assertRaises(StopIteration, cgen.next)
        self.assertRaises(StopIteration, cgen2.next)


class UnescapeTests(TestCase):

    def test_unescape_charref(self):
        from mechanize._html import unescape_charref
        mdash_utf8 = u"\u2014".encode("utf-8")
        for ref, codepoint, utf8, latin1 in [
            ("38", 38, u"&".encode("utf-8"), "&"),
            ("x2014", 0x2014, mdash_utf8, "&#x2014;"),
            ("8212", 8212, mdash_utf8, "&#8212;"),
            ]:
            self.assertEqual(unescape_charref(ref, None), unichr(codepoint))
            self.assertEqual(unescape_charref(ref, 'latin-1'), latin1)
            self.assertEqual(unescape_charref(ref, 'utf-8'), utf8)

    def test_unescape(self):
        import htmlentitydefs
        from mechanize._html import unescape
        data = "&amp; &lt; &mdash; &#8212; &#x2014;"
        mdash_utf8 = u"\u2014".encode("utf-8")
        ue = unescape(data, htmlentitydefs.name2codepoint, "utf-8")
        self.assertEqual("& < %s %s %s" % ((mdash_utf8,)*3), ue)

        for text, expect in [
            ("&a&amp;", "&a&"),
            ("a&amp;", "a&"),
            ]:
            got = unescape(text, htmlentitydefs.name2codepoint, "latin-1")
            self.assertEqual(got, expect)


# XXXXX these 'mock' classes are badly in need of simplification
class MockMethod:
    def __init__(self, meth_name, action, handle):
        self.meth_name = meth_name
        self.handle = handle
        self.action = action
    def __call__(self, *args):
        return apply(self.handle, (self.meth_name, self.action)+args)

class MockHeaders(UserDict.UserDict):
    def getallmatchingheaders(self, name):
        return ["%s: %s" % (k, v) for k, v in self.data.iteritems()]
    def getheaders(self, name):
        return self.data.values()

class MockResponse:
    closeable_response = None
    def __init__(self, url="http://example.com/", data=None, info=None):
        self.url = url
        self.fp = StringIO.StringIO(data)
        if info is None: info = {}
        self._info = MockHeaders(info)
        self.source = "%d%d" % (id(self), random.randint(0, sys.maxint-1))
    def info(self): return self._info
    def geturl(self): return self.url
    def read(self, size=-1): return self.fp.read(size)
    def seek(self, whence):
        assert whence == 0
        self.fp.seek(0)
    def close(self): pass
    def __getstate__(self):
        state = self.__dict__
        state['source'] = self.source
        return state
    def __setstate__(self, state):
        self.__dict__ = state

def make_mock_handler():
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
                if isinstance(response, urllib2.HTTPError):
                    raise response
                r = response
                r.seek(0)
            else:
                r = MockResponse()
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
    default_features = ["_seek"]
    default_others = []
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

        def same_response(ra, rb):
            return ra.source == rb.source

        b = TestBrowser()
        b.add_handler(make_mock_handler()([("http_open", None)]))
        self.assertRaises(mechanize.BrowserStateError, b.back)
        r1 = b.open("http://example.com/")
        self.assertRaises(mechanize.BrowserStateError, b.back)
        r2 = b.open("http://example.com/foo")
        self.assert_(same_response(b.back(), r1))
        r3 = b.open("http://example.com/bar")
        r4 = b.open("http://example.com/spam")
        self.assert_(same_response(b.back(), r3))
        self.assert_(same_response(b.back(), r1))
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

        # even if we get a HTTPError, history and .response() should still get updated
        error = urllib2.HTTPError("http://example.com/bad", 503, "Oops",
                                  MockHeaders(), StringIO.StringIO())
        b.add_handler(make_mock_handler()([("https_open", error)]))
        self.assertRaises(urllib2.HTTPError, b.open, "https://example.com/")
        self.assertEqual(b.response().geturl(), error.geturl())
        self.assert_(same_response(b.back(), r8))

        b.close()
        # XXX assert BrowserStateError

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
                r = b.open(url)
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
                r = b.open(url)
                self.assertEqual(b.viewing_html(), expect)

    def test_empty(self):
        import mechanize
        url = "http://example.com/"

        b = TestBrowser()
        b.add_handler(make_mock_handler()([("http_open", MockResponse(url, "", {}))]))
        r = b.open(url)
        self.assert_(not b.viewing_html())
        self.assertRaises(mechanize.BrowserStateError, b.links)
        self.assertRaises(mechanize.BrowserStateError, b.forms)
        self.assertRaises(mechanize.BrowserStateError, b.title)
        self.assertRaises(mechanize.BrowserStateError, b.select_form)
        self.assertRaises(mechanize.BrowserStateError, b.select_form,
                          name="blah")
        self.assertRaises(mechanize.BrowserStateError, b.find_link,
                          name="blah")

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
                          predicate=lambda x: True)
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
        r = MockResponse(url,
"""<html>
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
""", {"content-type": "text/html"})
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
        # now unknown methods are fed through to selected ClientForm.HTMLForm
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
        import urllib
        import mechanize
        from mechanize._html import clean_url
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

    def test_links(self):
        for factory_class in FACTORY_CLASSES:
            self._test_links(factory_class())
    def _test_links(self, factory):
        import mechanize
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

        Link = mechanize.Link
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
        import mechanize
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
        from mechanize import _Util

        br = TestBrowser()
        self.assertEqual(
            str(br),
            "<TestBrowser (not visiting a URL)>"
            )

        fp = StringIO.StringIO('<html><form name="f"><input /></form></html>')
        headers = mimetools.Message(
            StringIO.StringIO("Content-type: text/html"))
        response = _Util.response_seek_wrapper(_Util.closeable_response(
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


class UserAgentTests(TestCase):
    def test_set_handled_schemes(self):
        import mechanize
        class MockHandlerClass(make_mock_handler()):
            def __call__(self): return self
        class BlahHandlerClass(MockHandlerClass): pass
        class BlahProcessorClass(MockHandlerClass): pass
        BlahHandler = BlahHandlerClass([("blah_open", None)])
        BlahProcessor = BlahProcessorClass([("blah_request", None)])
        class TestUserAgent(mechanize.UserAgent):
            default_others = []
            default_features = []
            handler_classes = mechanize.UserAgent.handler_classes.copy()
            handler_classes.update(
                {"blah": BlahHandler, "_blah": BlahProcessor})
        ua = TestUserAgent()

        self.assertEqual(len(ua.handlers), 5)
        ua.set_handled_schemes(["http", "https"])
        self.assertEqual(len(ua.handlers), 2)
        self.assertRaises(ValueError,
            ua.set_handled_schemes, ["blah", "non-existent"])
        self.assertRaises(ValueError,
            ua.set_handled_schemes, ["blah", "_blah"])
        ua.set_handled_schemes(["blah"])

        req = mechanize.Request("blah://example.com/")
        r = ua.open(req)
        exp_calls = [("blah_open", (req,), {})]
        assert len(ua.calls) == len(exp_calls)
        for got, expect in zip(ua.calls, exp_calls):
            self.assertEqual(expect, got[1:])

        ua.calls = []
        req = mechanize.Request("blah://example.com/")
        ua._set_handler("_blah", True)
        r = ua.open(req)
        exp_calls = [
            ("blah_request", (req,), {}),
            ("blah_open", (req,), {})]
        assert len(ua.calls) == len(exp_calls)
        for got, expect in zip(ua.calls, exp_calls):
            self.assertEqual(expect, got[1:])
        ua._set_handler("_blah", True)

if __name__ == "__main__":
    import test_mechanize
    import doctest
    doctest.testmod(test_mechanize)
    import unittest
    unittest.main()
