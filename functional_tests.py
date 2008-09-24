#!/usr/bin/env python

# These tests access the network.

# thanks Moof (aka Giles Antonio Radford) for some of these

import os, sys, urllib, tempfile, errno
from unittest import TestCase

import mechanize
from mechanize import build_opener, install_opener, urlopen, urlretrieve
from mechanize import CookieJar, HTTPCookieProcessor, \
     HTTPHandler, HTTPRefreshProcessor, \
     HTTPEquivProcessor, HTTPRedirectHandler, \
     HTTPRedirectDebugProcessor, HTTPResponseDebugProcessor
from mechanize._rfc3986 import urljoin
from mechanize._util import hide_experimental_warnings, \
    reset_experimental_warnings

#from cookielib import CookieJar
#from urllib2 import build_opener, install_opener, urlopen
#from urllib2 import HTTPCookieProcessor, HTTPHandler

#from mechanize import CreateBSDDBCookieJar

## import logging
## logger = logging.getLogger("mechanize")
## logger.addHandler(logging.StreamHandler(sys.stdout))
## #logger.setLevel(logging.DEBUG)
## logger.setLevel(logging.INFO)


def sanepathname2url(path):
    import urllib
    urlpath = urllib.pathname2url(path)
    if os.name == "nt" and urlpath.startswith("///"):
        urlpath = urlpath[2:]
    # XXX don't ask me about the mac...
    return urlpath

class SimpleTests(TestCase):
    # thanks Moof (aka Giles Antonio Radford)

    def setUp(self):
        self.browser = mechanize.Browser()

    def test_simple(self):
        self.browser.open(self.uri)
        self.assertEqual(self.browser.title(), 'Python bits')
        # relative URL
        self.browser.open('/mechanize/')
        self.assertEqual(self.browser.title(), 'mechanize')

    def test_302_and_404(self):
        # the combination of 302 and 404 (/redirected is configured to redirect
        # to a non-existent URL /nonexistent) has caused problems in the past
        # due to accidental double-wrapping of the error response
        import urllib2
        self.assertRaises(
            urllib2.HTTPError,
            self.browser.open, urljoin(self.uri, "/redirected"),
            )

    def test_reread(self):
        # closing response shouldn't stop methods working (this happens also to
        # be true for e.g. mechanize.OpenerDirector when mechanize's own
        # handlers are in use, but is guaranteed to be true for
        # mechanize.Browser)
        r = self.browser.open(self.uri)
        data = r.read()
        r.close()
        r.seek(0)
        self.assertEqual(r.read(), data)
        self.assertEqual(self.browser.response().read(), data)

    def test_error_recovery(self):
        self.assertRaises(OSError, self.browser.open,
                          'file:///c|thisnoexistyiufheiurgbueirgbue')
        self.browser.open(self.uri)
        self.assertEqual(self.browser.title(), 'Python bits')

    def test_redirect(self):
        # 301 redirect due to missing final '/'
        r = self.browser.open(urljoin(self.uri, "bits"))
        self.assertEqual(r.code, 200)
        self.assert_("GeneralFAQ.html" in r.read(2048))

    def test_refresh(self):
        def refresh_request(seconds):
            uri = urljoin(self.uri, "/cgi-bin/cookietest.cgi")
            val = urllib.quote_plus('%d; url="%s"' % (seconds, self.uri))
            return uri + ("?refresh=%s" % val)
        self.browser.set_handle_refresh(True, honor_time=False)
        r = self.browser.open(refresh_request(5))
        self.assertEqual(r.geturl(), self.uri)
        # Set a maximum refresh time of 30 seconds (these long refreshes tend
        # to be there only because the website owner wants you to see the
        # latest news, or whatever -- they're not essential to the operation of
        # the site, and not really useful or appropriate when scraping).
        refresh_uri = refresh_request(60)
        self.browser.set_handle_refresh(True, max_time=30., honor_time=True)
        r = self.browser.open(refresh_uri)
        self.assertEqual(r.geturl(), refresh_uri)
        # allow long refreshes (but don't actually wait 60 seconds)
        self.browser.set_handle_refresh(True, max_time=None, honor_time=False)
        r = self.browser.open(refresh_request(60))
        self.assertEqual(r.geturl(), self.uri)

    def test_file_url(self):
        url = "file://%s" % sanepathname2url(
            os.path.abspath('functional_tests.py'))
        r = self.browser.open(url)
        self.assert_("this string appears in this file ;-)" in r.read())

    def test_open_local_file(self):
        # Since the file: URL scheme is not well standardised, Browser has a
        # special method to open files by name, for convenience:
        br = mechanize.Browser()
        response = br.open_local_file("mechanize/_mechanize.py")
        self.assert_("def open_local_file(self, filename):" in
                     response.get_data())

    def test_open_novisit(self):
        def test_state(br):
            self.assert_(br.request is None)
            self.assert_(br.response() is None)
            self.assertRaises(mechanize.BrowserStateError, br.back)
        test_state(self.browser)
        # note this involves a redirect, which should itself be non-visiting
        r = self.browser.open_novisit(urljoin(self.uri, "bits"))
        test_state(self.browser)
        self.assert_("GeneralFAQ.html" in r.read(2048))

    def test_non_seekable(self):
        # check everything still works without response_seek_wrapper and
        # the .seek() method on response objects
        ua = mechanize.UserAgent()
        ua.set_seekable_responses(False)
        ua.set_handle_equiv(False)
        response = ua.open(self.uri)
        self.failIf(hasattr(response, "seek"))
        data = response.read()
        self.assert_("Python bits" in data)


class ResponseTests(TestCase):

    def test_seek(self):
        br = mechanize.Browser()
        r = br.open(self.uri)
        html = r.read()
        r.seek(0)
        self.assertEqual(r.read(), html)

    def test_seekable_response_opener(self):
        opener = mechanize.OpenerFactory(
            mechanize.SeekableResponseOpener).build_opener()
        r = opener.open(urljoin(self.uri, "bits/cctest2.txt"))
        r.read()
        r.seek(0)
        self.assertEqual(r.read(),
                         r.get_data(),
                         "Hello ClientCookie functional test suite.\n")

    def test_seek_wrapper_class_name(self):
        opener = mechanize.UserAgent()
        opener.set_seekable_responses(True)
        try:
            opener.open(urljoin(self.uri, "nonexistent"))
        except mechanize.HTTPError, exc:
            self.assert_("HTTPError instance" in repr(exc))

    def test_no_seek(self):
        # should be possible to turn off UserAgent's .seek() functionality
        def check_no_seek(opener):
            r = opener.open(urljoin(self.uri, "bits/cctest2.txt"))
            self.assert_(not hasattr(r, "seek"))
            try:
                opener.open(urljoin(self.uri, "nonexistent"))
            except mechanize.HTTPError, exc:
                self.assert_(not hasattr(exc, "seek"))

        # mechanize.UserAgent
        opener = mechanize.UserAgent()
        opener.set_handle_equiv(False)
        opener.set_seekable_responses(False)
        opener.set_debug_http(False)
        check_no_seek(opener)

        # mechanize.OpenerDirector
        opener = mechanize.build_opener()
        check_no_seek(opener)

    def test_consistent_seek(self):
        # if we explicitly request that returned response objects have the
        # .seek() method, then raised HTTPError exceptions should also have the
        # .seek() method
        def check(opener, excs_also):
            r = opener.open(urljoin(self.uri, "bits/cctest2.txt"))
            data = r.read()
            r.seek(0)
            self.assertEqual(data, r.read(), r.get_data())
            try:
                opener.open(urljoin(self.uri, "nonexistent"))
            except mechanize.HTTPError, exc:
                data = exc.read()
                if excs_also:
                    exc.seek(0)
                    self.assertEqual(data, exc.read(), exc.get_data())
            else:
                self.assert_(False)

        opener = mechanize.UserAgent()
        opener.set_debug_http(False)

        # Here, only the .set_handle_equiv() causes .seek() to be present, so
        # exceptions don't necessarily support the .seek() method (and do not,
        # at present).
        opener.set_handle_equiv(True)
        opener.set_seekable_responses(False)
        check(opener, excs_also=False)

        # Here, (only) the explicit .set_seekable_responses() causes .seek() to
        # be present (different mechanism from .set_handle_equiv()).  Since
        # there's an explicit request, ALL responses are seekable, even
        # exception responses (HTTPError instances).
        opener.set_handle_equiv(False)
        opener.set_seekable_responses(True)
        check(opener, excs_also=True)

    def test_set_response(self):
        br = mechanize.Browser()
        r = br.open(self.uri)
        html = r.read()
        self.assertEqual(br.title(), "Python bits")

        newhtml = """<html><body><a href="spam">click me</a></body></html>"""

        r.set_data(newhtml)
        self.assertEqual(r.read(), newhtml)
        self.assertEqual(br.response().read(), html)
        br.response().set_data(newhtml)
        self.assertEqual(br.response().read(), html)
        self.assertEqual(list(br.links())[0].url, 'http://sourceforge.net')

        br.set_response(r)
        self.assertEqual(br.response().read(), newhtml)
        self.assertEqual(list(br.links())[0].url, "spam")

    def test_new_response(self):
        br = mechanize.Browser()
        data = "<html><head><title>Test</title></head><body><p>Hello.</p></body></html>"
        response = mechanize.make_response(
            data,
            [("Content-type", "text/html")],
            "http://example.com/",
            200,
            "OK"
            )
        br.set_response(response)
        self.assertEqual(br.response().get_data(), data)

    def hidden_test_close_pickle_load(self):
        print ("Test test_close_pickle_load is expected to fail unless Python "
               "standard library patch http://python.org/sf/1144636 has been "
               "applied")
        import pickle

        b = mechanize.Browser()
        r = b.open(urljoin(self.uri, "bits/cctest2.txt"))
        r.read()

        r.close()
        r.seek(0)
        self.assertEqual(r.read(),
                         "Hello ClientCookie functional test suite.\n")

        HIGHEST_PROTOCOL = -1
        p = pickle.dumps(b, HIGHEST_PROTOCOL)
        b = pickle.loads(p)
        r = b.response()
        r.seek(0)
        self.assertEqual(r.read(),
                         "Hello ClientCookie functional test suite.\n")


class FunctionalTests(TestCase):

    def test_referer(self):
        br = mechanize.Browser()
        br.set_handle_refresh(True, honor_time=False)
        referer = urljoin(self.uri, "bits/referertest.html")
        info = urljoin(self.uri, "/cgi-bin/cookietest.cgi")
        r = br.open(info)
        self.assert_(referer not in r.get_data())

        br.open(referer)
        r = br.follow_link(text="Here")
        self.assert_(referer in r.get_data())

    def test_cookies(self):
        import urllib2
        # this test page depends on cookies, and an http-equiv refresh
        #cj = CreateBSDDBCookieJar("/home/john/db.db")
        cj = CookieJar()
        handlers = [
            HTTPCookieProcessor(cj),
            HTTPRefreshProcessor(max_time=None, honor_time=False),
            HTTPEquivProcessor(),

            HTTPRedirectHandler(),  # needed for Refresh handling in 2.4.0
#            HTTPHandler(True),
#            HTTPRedirectDebugProcessor(),
#            HTTPResponseDebugProcessor(),
            ]

        o = apply(build_opener, handlers)
        try:
            install_opener(o)
            try:
                r = urlopen(urljoin(self.uri, "/cgi-bin/cookietest.cgi"))
            except urllib2.URLError, e:
                #print e.read()
                raise
            data = r.read()
            #print data
            self.assert_(
                data.find("Your browser supports cookies!") >= 0)
            self.assert_(len(cj) == 1)

            # test response.seek() (added by HTTPEquivProcessor)
            r.seek(0)
            samedata = r.read()
            r.close()
            self.assert_(samedata == data)
        finally:
            o.close()
            install_opener(None)

    def test_robots(self):
        plain_opener = mechanize.build_opener(mechanize.HTTPRobotRulesProcessor)
        browser = mechanize.Browser()
        for opener in plain_opener, browser:
            r = opener.open(urljoin(self.uri, "robots"))
            self.assertEqual(r.code, 200)
            self.assertRaises(
                mechanize.RobotExclusionError,
                opener.open, urljoin(self.uri, "norobots"))

    def test_urlretrieve(self):
        url = urljoin(self.uri, "/mechanize/")
        test_filename = "python.html"
        def check_retrieve(opener, filename, headers):
            self.assertEqual(headers.get('Content-Type'), 'text/html')
            f = open(filename)
            data = f.read()
            f.close()
            opener.close()
            from urllib import urlopen
            r = urlopen(url)
            self.assertEqual(data, r.read())
            r.close()

        opener = mechanize.build_opener()
        verif = CallbackVerifier(self)
        filename, headers = opener.retrieve(url, test_filename, verif.callback)
        try:
            self.assertEqual(filename, test_filename)
            check_retrieve(opener, filename, headers)
            self.assert_(os.path.isfile(filename))
        finally:
            os.remove(filename)

        opener = mechanize.build_opener()
        verif = CallbackVerifier(self)
        filename, headers = opener.retrieve(url, reporthook=verif.callback)
        check_retrieve(opener, filename, headers)
        # closing the opener removed the temporary file
        self.failIf(os.path.isfile(filename))

    def test_reload_read_incomplete(self):
        from mechanize import Browser
        browser = Browser()
        r1 = browser.open(urljoin(self.uri, "bits/mechanize_reload_test.html"))
        # if we don't do anything and go straight to another page, most of the
        # last page's response won't be .read()...
        r2 = browser.open(urljoin(self.uri, "mechanize"))
        self.assert_(len(r1.get_data()) < 4097)  # we only .read() a little bit
        # ...so if we then go back, .follow_link() for a link near the end (a
        # few kb in, past the point that always gets read in HTML files because
        # of HEAD parsing) will only work if it causes a .reload()...
        r3 = browser.back()
        browser.follow_link(text="near the end")
        # ... good, no LinkNotFoundError, so we did reload.
        # we have .read() the whole file
        self.assertEqual(len(r3._seek_wrapper__cache.getvalue()), 4202)

##     def test_cacheftp(self):
##         from urllib2 import CacheFTPHandler, build_opener
##         o = build_opener(CacheFTPHandler())
##         r = o.open("ftp://ftp.python.org/pub/www.python.org/robots.txt")
##         data1 = r.read()
##         r.close()
##         r = o.open("ftp://ftp.python.org/pub/www.python.org/2.3.2/announce.txt")
##         data2 = r.read()
##         r.close()
##         self.assert_(data1 != data2)


class CookieJarTests(TestCase):

    def test_mozilla_cookiejar(self):
        filename = tempfile.mktemp()
        try:
            def get_cookiejar():
                cj = mechanize.MozillaCookieJar(filename=filename)
                try:
                    cj.revert()
                except IOError, exc:
                    if exc.errno != errno.ENOENT:
                        raise
                return cj
            def commit(cj):
                cj.save()
            self._test_cookiejar(get_cookiejar, commit)
        finally:
            try:
                os.remove(filename)
            except OSError, exc:
                if exc.errno != errno.ENOENT:
                    raise

    def test_firefox3_cookiejar(self):
        try:
            mechanize.Firefox3CookieJar
        except AttributeError:
            # firefox 3 cookiejar is only supported in Python 2.5 and later;
            # also, sqlite3 must be available
            return

        filename = tempfile.mktemp()
        try:
            def get_cookiejar():
                hide_experimental_warnings()
                try:
                    cj = mechanize.Firefox3CookieJar(filename=filename)
                finally:
                    reset_experimental_warnings()
                cj.connect()
                return cj
            def commit(cj):
                pass
            self._test_cookiejar(get_cookiejar, commit)
        finally:
            os.remove(filename)

    def _test_cookiejar(self, get_cookiejar, commit):
        cookiejar = get_cookiejar()
        br = mechanize.Browser()
        br.set_cookiejar(cookiejar)
        br.set_handle_refresh(False)
        url = urljoin(self.uri, "/cgi-bin/cookietest.cgi")
        # no cookie was set on the first request
        html = br.open(url).read()
        self.assertEquals(html.find("Your browser supports cookies!"), -1)
        self.assertEquals(len(cookiejar), 1)
        # ... but now we have the cookie
        html = br.open(url).read()
        self.assert_("Your browser supports cookies!" in html)
        commit(cookiejar)

        # should still have the cookie when we load afresh
        cookiejar = get_cookiejar()
        br.set_cookiejar(cookiejar)
        html = br.open(url).read()
        self.assert_("Your browser supports cookies!" in html)


class CallbackVerifier:
    # for .test_urlretrieve()
    def __init__(self, testcase):
        self._count = 0
        self._testcase = testcase
    def callback(self, block_nr, block_size, total_size):
        self._testcase.assertEqual(block_nr, self._count)
        self._count = self._count + 1


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "test-tools")
    import testprogram
    USAGE_EXAMPLES = """
Examples:
  %(progName)s
                 - run all tests
  %(progName)s functional_tests.SimpleTests
                 - run all 'test*' test methods in class SimpleTests
  %(progName)s functional_tests.SimpleTests.test_redirect
                 - run SimpleTests.test_redirect

  %(progName)s -l
                 - start a local Twisted HTTP server and run the functional
                   tests against that, rather than against SourceForge
                   (quicker!)
                   If this option doesn't work on Windows/Mac, somebody please
                   tell me about it, or I'll never find out...
"""
    prog = testprogram.TestProgram(
        ["functional_tests"],
        localServerProcess=testprogram.TwistedServerProcess(),
        usageExamples=USAGE_EXAMPLES,
        )
    result = prog.runTests()
