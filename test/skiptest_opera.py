"""Some cookie tests from the testsuites.opera.com website.

These are skipped by test.py since they access the internet even when the --uri
option is not passed to the test runner.

TODO: get the source code for these tests and run them locally if feasible
"""

import os
import posixpath

import mechanize
from mechanize._util import read_file, write_file

from test.test_functional import TestCase


def ensure_trailing_newline(text):
    if not text.endswith("\n"):
        return text + "\n"
    return text


class OperaCookieTests(TestCase):

    OPERA_COOKIE_TEST_URIS_FILENAME = "opera_cookie_test_uris"

    OPERA_COOKIE_TEST_URIS_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        OPERA_COOKIE_TEST_URIS_FILENAME)

    @classmethod
    def fetch_test_uris(cls):
        browser = mechanize.Browser()
        test_page = "http://testsuites.opera.com/cookies/"
        browser.open(test_page)
        # TODO: These exclusions are all failing.  Uncomment the subset of
        # these tests that aren't failing due to lack of JS support or similar.
        exclusions = set([
                "http://testsuites.opera.com/cookies/002.php",
                "http://testsuites.opera.com/cookies/004/004.php",
                # uses JS
                "http://testsuites.opera.com/cookies/009.php",
                # uses JS
                "http://testsuites.opera.com/cookies/010.php",
                "http://testsuites.opera.com/cookies/012.php",
                # the test_page URI comments that this "Needs restart"
                "http://testsuites.opera.com/cookies/013.php",
                # traceback
                "http://testsuites.opera.com/cookies/014/014.php",
                # uses JS
                "http://testsuites.opera.com/cookies/017.php",
                "http://testsuites.opera.com/cookies/201.php",
                "http://testsuites.opera.com/cookies/202.php",
                "http://testsuites.opera.com/cookies/203.php",
                "http://testsuites.opera.com/cookies/204.php",
                "http://testsuites.opera.com/cookies/205.php",
                "http://testsuites.opera.com/cookies/206.php",
                # traceback; the test_page URI comments that this "Needs
                # restart"
                "http://testsuites.opera.com/cookies/301.php",
                "http://testsuites.opera.com/cookies/302/302.php",
                "http://testsuites.opera.com/cookies/303.php",
                "http://testsuites.opera.com/cookies/304.php",
                "http://testsuites.opera.com/cookies/305.php",
                "http://testsuites.opera.com/cookies/306.php",
                "http://testsuites.opera.com/cookies/307.php",
                # traceback
                "http://testsuites.opera.com/cookies/308.php",
                "http://testsuites.opera.com/cookies/308b.php",
                "http://testsuites.opera.com/cookies/309.php",
                "http://testsuites.opera.com/cookies/309b.php",
                # the test_page URI comments that this "Needs ... deletion of
                # all cookies first"
                "http://testsuites.opera.com/cookies/310.php",
                # the test_page URI comments that this "Might need deletion of
                # all cookies first"
                "http://testsuites.opera.com/cookies/313.php",
                # the test_page URI comments "Needs UI" re these two
                "http://testsuites.opera.com/cookies/501.php",
                "http://testsuites.opera.com/cookies/502.php",
                ])
        uris = []
        for link in browser.links():
            uri = link.absolute_url
            if uri not in exclusions:
                uris.append(uri)
        return uris

    @classmethod
    def write_test_uris(cls):
        uris = cls.fetch_test_uris()
        write_file(cls.OPERA_COOKIE_TEST_URIS_PATH,
                   ensure_trailing_newline("\n".join(uris)))

    @classmethod
    def make_test(cls, uri):
        def test(self):
            browser = self.make_browser()
            browser.open(uri)
            self.assertIn("<p>PASS</p>", browser.response().get_data())
        scheme, authority, path, query, fragment = \
            mechanize._rfc3986.urlsplit(uri)
        name = posixpath.splitext(posixpath.basename(path))[0]
        method_name = "test_%s" % name
        test.__name__ = method_name
        return test

    @classmethod
    def add_test(cls, uri):
        test = cls.make_test(uri)
        setattr(cls, test.__name__, test)

    @classmethod
    def add_tests(cls):
        if not os.path.exists(cls.OPERA_COOKIE_TEST_URIS_PATH):
            return

        for uri in read_file(cls.OPERA_COOKIE_TEST_URIS_PATH).splitlines():
            cls.add_test(uri)

OperaCookieTests.add_tests()
