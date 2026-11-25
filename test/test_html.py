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
        br.set_html("</base>")
        list(br.links())

    def test_bad_base_tag(self):
        # a document with a base tag with no href used to cause an exception
        br = mechanize.Browser()
        br.set_html(
            "<BASE TARGET='_main'><a href='http://example.com/'>eg</a>",
            url="http://example.com/",
        )
        list(br.links())


class BaseURLTests(TestCase):

    document_url = 'https://example.test/docs/index.html'
    relative_bases = [
        ('assets/', 'https://example.test/docs/assets/'),
        ('../assets/', 'https://example.test/assets/'),
        ('/assets/', 'https://example.test/assets/'),
        ('//cdn.example.test/assets/', 'https://cdn.example.test/assets/'),
        ('https://cdn.example.test/assets/', 'https://cdn.example.test/assets/'),
        (' /assets/ ', 'https://example.test/assets/'),
    ]

    def browser(self, html, url=document_url):
        br = mechanize.Browser()
        br.set_html(html, url=url)
        return br

    def link_urls(self, br):
        return [link.absolute_url for link in br.links()]

    def form_actions(self, br):
        return [form.action for form in br.forms()]

    def test_relative_base_links(self):
        for href, expected_base in self.relative_bases:
            with self.subTest(href=href):
                br = self.browser(
                    '<base href="%s"><a href="chapter.html">chapter</a>' % href)
                self.assertEqual(br.find_link().absolute_url,
                                 expected_base + 'chapter.html')
                self.assertEqual(br.click_link().get_full_url(),
                                 expected_base + 'chapter.html')

    def test_relative_base_form_actions(self):
        for href, expected_base in self.relative_bases:
            with self.subTest(href=href):
                br = self.browser(
                    '<base href="%s"><form action="submit" method="post">'
                    '<input name="q" value="test"></form>' % href)
                br.select_form(nr=0)
                self.assertEqual(br.form.action, expected_base + 'submit')
                self.assertEqual(br.click().get_full_url(),
                                 expected_base + 'submit')

    def test_first_base_wins(self):
        br = self.browser(
            '<base href="/a/"><base href="b/"><base href="https://x.test/">'
            '<a href="c.html">c</a><form action="s"></form>')
        self.assertEqual(self.link_urls(br), ['https://example.test/a/c.html'])
        self.assertEqual(self.form_actions(br), ['https://example.test/a/s'])

    def test_empty_base_href_wins(self):
        br = self.browser(
            '<base href=""><base href="/a/"><a href="c.html">c</a>',
            url='https://example.test/docs/index.html?q=1#frag')
        self.assertEqual(self.link_urls(br),
                         ['https://example.test/docs/c.html'])

    def test_uppercase_base(self):
        br = self.browser('<BASE HREF="/a/"><A HREF="c.html">c</A>')
        self.assertEqual(self.link_urls(br), ['https://example.test/a/c.html'])

    def test_document_url_with_query_and_fragment(self):
        br = self.browser(
            '<base href="?z"><a href="#x">x</a><form action="s"></form>',
            url='https://example.test/docs/index.html?q=1#frag')
        self.assertEqual(self.link_urls(br),
                         ['https://example.test/docs/index.html?z#x'])
        self.assertEqual(self.form_actions(br), ['https://example.test/docs/s'])

    def test_base_in_foreign_content_or_template_is_ignored(self):
        for wrapper in ('svg', 'math', 'template'):
            with self.subTest(wrapper=wrapper):
                br = self.browser(
                    '<%s><base href="/ignored/"></%s><base href="/a/">'
                    '<a href="c.html">c</a><form action="s"></form>'
                    % (wrapper, wrapper))
                self.assertEqual(self.link_urls(br),
                                 ['https://example.test/a/c.html'])
                self.assertEqual(self.form_actions(br),
                                 ['https://example.test/a/s'])

    def test_relative_base_with_opaque_document_url(self):
        br = self.browser(
            '<base href="/a/"><a href="https://x.test/c">c</a>',
            url='about:blank')
        self.assertEqual(br.links()[0].base_url, 'about:blank')
        br = self.browser(
            '<base href="https://x.test/a/"><a href="c">c</a>',
            url='about:blank')
        self.assertEqual(self.link_urls(br), ['https://x.test/a/c'])

    def test_deeply_nested_document(self):
        depth = 5000
        br = self.browser(
            '<div>' * depth + '<base href="/a/"><a href="c.html">c</a>'
            + '</div>' * depth)
        self.assertEqual(self.link_urls(br), ['https://example.test/a/c.html'])

    def test_formaction_resolved_against_base(self):
        br = self.browser(
            '<base href="/a/"><form action="s">'
            '<input type="submit" name="b" formaction="x">'
            '<input type="submit" name="d"></form>')
        br.select_form(nr=0)
        self.assertEqual(br.click(name='b').get_full_url(),
                         'https://example.test/a/x?b=')
        self.assertEqual(br.click(name='d').get_full_url(),
                         'https://example.test/a/s?d=')
        self.assertEqual(br.form.action, 'https://example.test/a/s')

    def test_base_without_href_is_skipped(self):
        br = self.browser(
            '<base target="_top"><base href="/a/">'
            '<a href="c.html">c</a><form action="s"></form>')
        self.assertEqual(self.link_urls(br), ['https://example.test/a/c.html'])
        self.assertEqual(self.form_actions(br), ['https://example.test/a/s'])

    def test_base_applies_to_preceding_content(self):
        br = self.browser(
            '<a href="c0.html">c0</a><form action="s0"></form>'
            '<base href="/a/"><a href="c1.html">c1</a>'
            '<form action="s1"></form>')
        self.assertEqual(self.link_urls(br), [
            'https://example.test/a/c0.html', 'https://example.test/a/c1.html'])
        self.assertEqual(self.form_actions(br), [
            'https://example.test/a/s0', 'https://example.test/a/s1'])

    def test_form_without_action_submits_to_document_url(self):
        for href in ('#top', 'https://cdn.example.test/assets/'):
            br = self.browser(
                '<base href="%s"><form></form><form action=""></form>' % href)
            self.assertEqual(self.form_actions(br),
                             [self.document_url, self.document_url])

    def test_no_base(self):
        br = self.browser('<a href="c.html">c</a><form action="s"></form>')
        self.assertEqual(self.link_urls(br),
                         ['https://example.test/docs/c.html'])
        self.assertEqual(self.form_actions(br),
                         ['https://example.test/docs/s'])

    def test_no_document_url(self):
        root = content_parser(
            b'<base href="https://x.test/a/"><a href="c.html">c</a>'
            b'<form action="s"></form><form></form>')
        links = list(mechanize._html.iterlinks(root, None))
        self.assertEqual([link.absolute_url for link in links],
                         ['https://x.test/a/c.html'])
        forms, _ = mechanize._form.parse_forms(root, None)
        self.assertEqual([form.action for form in forms],
                         ['https://x.test/a/s', 'https://x.test/a/'])


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

    def test_util_func(self):
        headers1 = str(test_html_response('').info())
        headers2 = str(test_html_response('').info())
        self.assertEqual(headers1, headers2)

    def test_link_parsing(self):

        def get_first_link_text(html):
            factory = Factory()
            response = test_html_response(html, url="http://example.com/")
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
