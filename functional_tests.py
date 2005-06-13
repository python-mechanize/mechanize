#!/usr/bin/env python

from unittest import TestCase

import mechanize

class ResponseTests(TestCase):
    def test_close_pickle_load(self):
        print ("This test is expected to fail unless Python standard library"
               "patch http://python.org/sf/1144636 has been applied")
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
