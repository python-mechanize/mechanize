#!/usr/bin/env python

# These tests access the network.

import os
from unittest import TestCase

import mechanize
from mechanize import build_opener, install_opener, urlopen, urlretrieve
from mechanize import CookieJar, HTTPCookieProcessor, \
     HTTPHandler, HTTPRefreshProcessor, \
     HTTPEquivProcessor, HTTPRedirectHandler, \
     HTTPRedirectDebugProcessor, HTTPResponseDebugProcessor

#from cookielib import CookieJar
#from urllib2 import build_opener, install_opener, urlopen
#from urllib2 import HTTPCookieProcessor, HTTPHandler

#from ClientCookie import CreateBSDDBCookieJar

## logger = ClientCookie.getLogger("ClientCookie")
## logger.addHandler(ClientCookie.StreamHandler())
## logger.setLevel(ClientCookie.DEBUG)


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
        self.browser.open('http://wwwsearch.sourceforge.net/')
        self.assertEqual(self.browser.title(), 'Python bits')
        # relative URL
        self.browser.open('/mechanize/')
        self.assertEqual(self.browser.title(), 'mechanize')

    def test_reread(self):
        r = self.browser.open('http://wwwsearch.sourceforge.net/')
        data = r.read()
        r.close()
        r.seek(0)
        self.assertEqual(r.read(), data)
        self.assertEqual(self.browser.response().read(), data)

    def test_error_recovery(self):
        self.assertRaises(OSError, self.browser.open,
                          'file:///c|thisnoexistyiufheiurgbueirgbue')
        self.browser.open('http://wwwsearch.sourceforge.net/')
        self.assertEqual(self.browser.title(), 'Python bits')

    def test_redirect(self):
        # 302 redirect due to missing final '/'
        self.browser.open('http://wwwsearch.sourceforge.net')

    def test_file_url(self):
        url = "file://%s" % sanepathname2url(
            os.path.abspath('functional_tests.py'))
        self.browser.open(url)


class ResponseTests(TestCase):

    def test_seek(self):
        from mechanize import Browser
        br = Browser()
        r = br.open("http://wwwsearch.sourceforge.net/")
        html = r.read()
        r.seek(0)
        self.assertEqual(r.read(), html)

    def test_response_close_and_read(self):
        opener = ClientCookie.build_opener(ClientCookie.SeekableProcessor)
        r = opener.open("http://wwwsearch.sf.net/bits/cctest2.txt")
        # closing response shouldn't stop methods working if we're using
        # SeekableProcessor (ie. _Util.response_seek_wrapper)
        r.read()
        r.close()
        r.seek(0)
        self.assertEqual(r.read(), "Hello ClientCookie functional test suite.\n")

    def test_set_response(self):
        from mechanize import Browser
        br = Browser()
        r = br.open("http://wwwsearch.sourceforge.net/")
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

    def test_close_pickle_load(self):
        print ("Test test_close_pickle_load is expected to fail unless Python "
               "standard library patch http://python.org/sf/1144636 has been "
               "applied")
        import pickle

        b = mechanize.Browser()
        r = b.open("http://wwwsearch.sf.net/bits/cctest2.txt")
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
    def test_clientcookie(self):
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
                r = urlopen("http://wwwsearch.sf.net/cgi-bin/cookietest.cgi")
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
            # uninstall opener (don't try this at home)
            ClientCookie._urllib2_support._opener = None

    def test_urlretrieve(self):
        url = "http://www.python.org/"
        verif = CallbackVerifier(self)
        fn, hdrs = urlretrieve(url, "python.html", verif.callback)
        try:
            f = open(fn)
            data = f.read()
            f.close()
        finally:
            os.remove(fn)
        r = urlopen(url)
        self.assert_(data == r.read())
        r.close()

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

class CallbackVerifier:
    # for .test_urlretrieve()
    def __init__(self, testcase):
        self._count = 0
        self._testcase = testcase
    def callback(self, block_nr, block_size, total_size):
        if block_nr != self._count:
            self._testcase.fail()
        self._count = self._count + 1


if __name__ == "__main__":
    import unittest
    unittest.main()
