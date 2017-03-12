#!/usr/bin/env python

from unittest import TestCase

import mechanize
import mechanize._form
from mechanize._response import test_html_response


class RegressionTests(TestCase):

    def test_close_base_tag(self):
        # any document containing a </base> tag used to cause an exception
        br = mechanize.Browser()
        response = test_html_response("</base>")
        br.set_response(response)
        list(br.links())

    def test_bad_base_tag(self):
        # a document with a base tag with no href used to cause an exception
        br = mechanize.Browser()
        response = test_html_response(
            "<BASE TARGET='_main'><a href='http://example.com/'>eg</a>")
        br.set_response(response)
        list(br.links())


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
        self.assertEqual("& < %s %s %s" % ((mdash_utf8,) * 3), ue)

        for text, expect in [
            ("&a&amp;", "&a&"),
            ("a&amp;", "a&"),
        ]:
            got = unescape(text, htmlentitydefs.name2codepoint, "latin-1")
            self.assertEqual(got, expect)


class EncodingFinderTests(TestCase):

    def make_response(self, encodings):
        return mechanize._response.test_response(
            headers=[("Content-type", "text/html; charset=\"%s\"" % encoding)
                     for encoding in encodings])

    def test_known_encoding(self):
        encoding_finder = mechanize._html.EncodingFinder("default")
        response = self.make_response(["utf-8"])
        self.assertEqual(encoding_finder.encoding(response), "utf-8")

    def test_unknown_encoding(self):
        encoding_finder = mechanize._html.EncodingFinder("default")
        response = self.make_response(["bogus"])
        self.assertEqual(encoding_finder.encoding(response), "default")

    def test_precedence(self):
        encoding_finder = mechanize._html.EncodingFinder("default")
        response = self.make_response(["latin-1", "utf-8"])
        self.assertEqual(encoding_finder.encoding(response), "latin-1")

    def test_fallback(self):
        encoding_finder = mechanize._html.EncodingFinder("default")
        response = self.make_response(["bogus", "utf-8"])
        self.assertEqual(encoding_finder.encoding(response), "utf-8")


if __name__ == "__main__":
    import unittest
    unittest.main()
