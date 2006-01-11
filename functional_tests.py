#!/usr/bin/env python

import os
from unittest import TestCase

import mechanize

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


if __name__ == "__main__":
    import unittest
    unittest.main()
