#!/usr/bin/env python

from unittest import TestCase

import mechanize
import mechanize._form
from mechanize._response import test_html_response
from mechanize._html import content_parser, get_title, Factory


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


class TitleTests(TestCase):

    def test_title_parsing(self):
        html = ("""\
<html><head>
<title> Title\n Test</title>
</head><body><p>Blah.<p></body></html>
""")
        self.assertEqual(get_title(content_parser(html)), 'Title Test')


class MiscTests(TestCase):

    def test_link_parsing(self):

        def get_first_link_text(html):
            factory = Factory()
            response = test_html_response(html)
            factory.set_response(response)
            return list(factory.links())[0].text

        html = ("""\
        <html><head><title>Title</title></head><body>
        <p><a href="http://example.com/">The  quick\tbrown fox jumps
        over the <i><b>lazy</b></i> dog </a>
        </body></html>
        """)
        self.assertEqual(
            get_first_link_text(html), u'The quick brown fox jumps over the lazy dog')

        html = ("""\
        <html><head><title>Title</title></head><body>
        <p><a href="http://example.com/"></a>
        </body></html>
        """)
        self.assertEqual(get_first_link_text(html), '')

        html = ("""\
        <html><head><title>Title</title></head><body>
        <p><iframe src="http://example.com/"></iframe>
        </body></html>
        """)
        self.assertEqual(get_first_link_text(html), '')

    def test_title_parsing(self):
        def get_title(html):
            factory = Factory()
            response = test_html_response(html)
            factory.set_response(response)
            return factory.title

        html = (b"""\
        <html><head>
        <title>T&gt;itle</title>
        </head><body><p>Blah.<p></body></html>
        """)
        self.assertEqual(get_title(html), u'T>itle')

        html = ("""\
        <html><head>
        <title>  Ti<script type="text/strange">alert("this is valid HTML -- yuck!")</script>
        tle &amp;&#38;
        </title>
        </head><body><p>Blah.<p></body></html>
        """)
        self.assertEqual(
            str(get_title(html)), 'Ti<script type="text/strange">alert("this is valid HTML -- yuck!")</script> tle &&')

        html = ("""\
        <html><head>
        <title>""")
        self.assertEqual(get_title(html), u'')


if __name__ == "__main__":
    import unittest
    unittest.main()
