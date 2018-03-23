import pickle
import importlib

import mechanize
import mechanize._response
import mechanize._testcase
from mechanize.polyglot import is_py2

pickle_modules = [pickle]
if is_py2:
    pickle_modules.append(importlib.import_module('cPickle'))


def pickle_and_unpickle(obj, implementation):
    return implementation.loads(implementation.dumps(obj))


def test_pickling(obj, check=lambda unpickled: None):
    for pm in pickle_modules:
        check(pickle_and_unpickle(obj, pm))


class PickleTest(mechanize._testcase.TestCase):

    def test_pickle_cookie(self):
        from mechanize._clientcookie import cookies_equal
        cookiejar = mechanize.CookieJar()
        url = "http://example.com/"
        request = mechanize.Request(url)
        response = mechanize._response.test_response(
            headers=[("Set-Cookie", "spam=eggs")], url=url)
        [cookie] = cookiejar.make_cookies(response, request)

        def check_equality(b):
            self.assertTrue(cookies_equal(cookie, b))

        test_pickling(cookie, check_equality)

    def test_pickle_cookiejar(self):
        test_pickling(mechanize.CookieJar())


if __name__ == "__main__":
    mechanize._testcase.main()
