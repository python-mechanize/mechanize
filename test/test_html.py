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
        for factory in [mechanize.DefaultFactory(), mechanize.RobustFactory()]:
            br = mechanize.Browser(factory=factory)
            response = test_html_response(
                "<BASE TARGET='_main'><a href='http://example.com/'>eg</a>")
            br.set_response(response)
            list(br.links())

    def test_robust_form_parser_uses_beautifulsoup(self):
        factory = mechanize.RobustFormsFactory()
        self.assertIs(factory.form_parser_class,
                      mechanize._form.RobustFormParser)

    def test_form_parser_does_not_use_beautifulsoup(self):
        factory = mechanize.FormsFactory()
        self.assertIs(factory.form_parser_class, mechanize._form.FormParser)

    def _make_forms_from_bad_html(self, factory):
        bad_html = "<! -- : -- >"
        factory.set_response(test_html_response(bad_html), "utf-8")
        return list(factory.forms())

    def test_robust_form_parser_does_not_raise_on_bad_html(self):
        self._make_forms_from_bad_html(mechanize.RobustFormsFactory())

    def test_form_parser_fails_on_bad_html(self):
        self.assertRaises(
            mechanize.ParseError,
            self._make_forms_from_bad_html, mechanize.FormsFactory())


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


if __name__ == "__main__":
    import unittest
    unittest.main()
