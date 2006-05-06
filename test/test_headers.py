"""Tests for ClientCookie._HeadersUtil."""

from unittest import TestCase

try: True
except NameError:
    True = 1
    False = 0

class IsHtmlTests(TestCase):
    def test_is_html(self):
        from ClientCookie._HeadersUtil import is_html
        for allow_xhtml in False, True:
            for cths, ext, expect in [
                (["text/html"], ".html", True),
                (["text/html", "text/plain"], ".html", True),
                # Content-type takes priority over file extension from URL
                (["text/html"], ".txt", True),
                (["text/plain"], ".html", False),
                # use extension if no Content-Type
                ([], ".html", True),
                ([], ".gif", False),
                # don't regard XHTML as HTML (unless user explicitly asks for it),
                # since we don't yet handle XML properly
                ([], ".xhtml", allow_xhtml),
                (["text/xhtml"], ".xhtml", allow_xhtml),
                ]:
                url = "http://example.com/foo"+ext
                self.assertEqual(expect, is_html(cths, url, allow_xhtml))

class HeaderTests(TestCase):
    def test_parse_ns_headers(self):
        from ClientCookie._HeadersUtil import parse_ns_headers

        # quotes should be stripped
        assert parse_ns_headers(['foo=bar; expires=01 Jan 2040 22:23:32 GMT']) == \
               [[('foo', 'bar'), ('expires', 2209069412L), ('version', '0')]]
        assert parse_ns_headers(['foo=bar; expires="01 Jan 2040 22:23:32 GMT"']) == \
               [[('foo', 'bar'), ('expires', 2209069412L), ('version', '0')]]

    def test_parse_ns_headers_special_names(self):
        # names such as 'expires' are not special in first name=value pair
        # of Set-Cookie: header
        from ClientCookie._HeadersUtil import parse_ns_headers

        # Cookie with name 'expires'
        hdr = 'expires=01 Jan 2040 22:23:32 GMT'
        expected = [[("expires", "01 Jan 2040 22:23:32 GMT"), ("version", "0")]]
        self.assertEquals(parse_ns_headers([hdr]), expected)

    def test_join_header_words(self):
        from ClientCookie._HeadersUtil import join_header_words

        assert join_header_words([[
            ("foo", None), ("bar", "baz"), (None, "value")
            ]]) == "foo; bar=baz; value"

        assert join_header_words([[]]) == ""

    def test_split_header_words(self):
        from ClientCookie._HeadersUtil import split_header_words

        tests = [
            ("foo", [[("foo", None)]]),
            ("foo=bar", [[("foo", "bar")]]),
            ("   foo   ", [[("foo", None)]]),
            ("   foo=   ", [[("foo", "")]]),
            ("   foo=", [[("foo", "")]]),
            ("   foo=   ; ", [[("foo", "")]]),
            ("   foo=   ; bar= baz ", [[("foo", ""), ("bar", "baz")]]),
            ("foo=bar bar=baz", [[("foo", "bar"), ("bar", "baz")]]),
            # doesn't really matter if this next fails, but it works ATM
            ("foo= bar=baz", [[("foo", "bar=baz")]]),
            ("foo=bar;bar=baz", [[("foo", "bar"), ("bar", "baz")]]),
            ('foo bar baz', [[("foo", None), ("bar", None), ("baz", None)]]),
            ("a, b, c", [[("a", None)], [("b", None)], [("c", None)]]),
            (r'foo; bar=baz, spam=, foo="\,\;\"", bar= ',
             [[("foo", None), ("bar", "baz")],
              [("spam", "")], [("foo", ',;"')], [("bar", "")]]),
            ]

        for arg, expect in tests:
            try:
                result = split_header_words([arg])
            except:
                import traceback, StringIO
                f = StringIO.StringIO()
                traceback.print_exc(None, f)
                result = "(error -- traceback follows)\n\n%s" % f.getvalue()
            assert result == expect, """
When parsing: '%s'
Expected:     '%s'
Got:          '%s'
""" % (arg, expect, result)

    def test_roundtrip(self):
        from ClientCookie._HeadersUtil import split_header_words, join_header_words

        tests = [
            ("foo", "foo"),
            ("foo=bar", "foo=bar"),
            ("   foo   ", "foo"),
            ("foo=", 'foo=""'),
            ("foo=bar bar=baz", "foo=bar; bar=baz"),
            ("foo=bar;bar=baz", "foo=bar; bar=baz"),
            ('foo bar baz', "foo; bar; baz"),
            (r'foo="\"" bar="\\"', r'foo="\""; bar="\\"'),
            ('foo,,,bar', 'foo, bar'),
            ('foo=bar,bar=baz', 'foo=bar, bar=baz'),

            ('text/html; charset=iso-8859-1',
             'text/html; charset="iso-8859-1"'),

            ('foo="bar"; port="80,81"; discard, bar=baz',
             'foo=bar; port="80,81"; discard, bar=baz'),

            (r'Basic realm="\"foo\\\\bar\""',
             r'Basic; realm="\"foo\\\\bar\""')
            ]

        for arg, expect in tests:
            input = split_header_words([arg])
            res = join_header_words(input)
            assert res == expect, """
When parsing: '%s'
Expected:     '%s'
Got:          '%s'
Input was:    '%s'""" % (arg, expect, res, input)


if __name__ == "__main__":
    import unittest
    unittest.main()
