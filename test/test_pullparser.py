#!/usr/bin/env python

from unittest import TestCase

def peek_token(p):
    tok = p.get_token()
    p.unget_token(tok)
    return tok


class PullParserTests(TestCase):
    from mechanize._pullparser import PullParser, TolerantPullParser
    PARSERS = [(PullParser, False), (TolerantPullParser, True)]

    def data_and_file(self):
        from StringIO import StringIO
        data = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title an=attr>Title</title>
</head>
<body>
<p>This is a data <img alt="blah &amp; &#097;"> &amp; that was an entityref and this &#097; is
a charref.  <blah foo="bing" blam="wallop">.
<!-- comment blah blah
still a comment , blah and a space at the end 
-->
<!rheum>
<?rhaponicum>
<randomtag spam="eggs"/>
</body>
</html>
""" #"
        f = StringIO(data)
        return data, f

    def test_encoding(self):
        #from mechanize import _pullparser
        #for pc, tolerant in [(_pullparser.PullParser, False)]:#PullParserTests.PARSERS:
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_encoding(pc, tolerant)
    def _test_encoding(self, parser_class, tolerant):
        from StringIO import StringIO
        datas = ["<a>&#1092;</a>", "<a>&#x444;</a>"]
        def get_text(data, encoding):
            p = _get_parser(data, encoding)
            p.get_tag("a")
            return p.get_text()
        def get_attr(data, encoding, et_name, attr_name):
            p = _get_parser(data, encoding)
            while True:
                tag = p.get_tag(et_name)
                attrs = tag.attrs
                if attrs is not None:
                    break
            return dict(attrs)[attr_name]
        def _get_parser(data, encoding):
            f = StringIO(data)
            p = parser_class(f, encoding=encoding)
            #print 'p._entitydefs>>%s<<' % p._entitydefs['&mdash;']
            return p

        for data in datas:
            self.assertEqual(get_text(data, "KOI8-R"), "\xc6")
            self.assertEqual(get_text(data, "UTF-8"), "\xd1\x84")

        self.assertEqual(get_text("<a>&mdash;</a>", "UTF-8"),
                         u"\u2014".encode('utf8'))
        self.assertEqual(
            get_attr('<a name="&mdash;">blah</a>', "UTF-8", "a", "name"),
            u"\u2014".encode('utf8'))
        self.assertEqual(get_text("<a>&mdash;</a>", "ascii"), "&mdash;")

#        response = urllib.addinfourl(f, {"content-type": "text/html; charset=XXX"}, req.get_full_url())
    def test_get_token(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_get_token(pc, tolerant)
    def _test_get_token(self, parser_class, tolerant):
        data, f = self.data_and_file()
        p = parser_class(f)
        from mechanize._pullparser import NoMoreTokensError
        self.assertEqual(
            p.get_token(), ("decl",
'''DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd"''', None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("starttag", "html", []))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("starttag", "head", []))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("starttag", "title", [("an", "attr")]))
        self.assertEqual(p.get_token(), ("data", "Title", None))
        self.assertEqual(p.get_token(), ("endtag", "title", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("endtag", "head", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("starttag", "body", []))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("starttag", "p", []))
        self.assertEqual(p.get_token(), ("data", "This is a data ", None))
        self.assertEqual(p.get_token(), ("starttag", "img", [("alt", "blah & a")]))
        self.assertEqual(p.get_token(), ("data", " ", None))
        self.assertEqual(p.get_token(), ("entityref", "amp", None))
        self.assertEqual(p.get_token(), ("data",
                                         " that was an entityref and this ",
                                         None))
        self.assertEqual(p.get_token(), ("charref", "097", None))
        self.assertEqual(p.get_token(), ("data", " is\na charref.  ", None))
        self.assertEqual(p.get_token(), ("starttag", "blah",
                                         [("foo", "bing"), ("blam", "wallop")]))
        self.assertEqual(p.get_token(), ("data", ".\n", None))
        self.assertEqual(p.get_token(), (
            "comment", " comment blah blah\n"
            "still a comment , blah and a space at the end \n", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("decl", "rheum", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("pi", "rhaponicum", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), (
            (tolerant and "starttag" or "startendtag"), "randomtag",
            [("spam", "eggs")]))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("endtag", "body", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertEqual(p.get_token(), ("endtag", "html", None))
        self.assertEqual(p.get_token(), ("data", "\n", None))
        self.assertRaises(NoMoreTokensError, p.get_token)
#        print "token", p.get_token()
#        sys.exit()

    def test_unget_token(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_unget_token(pc, tolerant)
    def _test_unget_token(self, parser_class, tolerant):
        data, f = self.data_and_file()
        p = parser_class(f)
        p.get_token()
        tok = p.get_token()
        self.assertEqual(tok, ("data", "\n", None))
        p.unget_token(tok)
        self.assertEqual(p.get_token(), ("data", "\n", None))
        tok = p.get_token()
        self.assertEqual(tok, ("starttag", "html", []))
        p.unget_token(tok)
        self.assertEqual(tok, ("starttag", "html", []))

    def test_get_tag(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_get_tag(pc, tolerant)
    def _test_get_tag(self, parser_class, tolerant):
        from mechanize._pullparser import NoMoreTokensError
        data, f = self.data_and_file()
        p = parser_class(f)
        self.assertEqual(p.get_tag(), ("starttag", "html", []))
        self.assertEqual(p.get_tag("blah", "body", "title"),
                     ("starttag", "title", [("an", "attr")]))
        self.assertEqual(p.get_tag(), ("endtag", "title", None))
        self.assertEqual(p.get_tag("randomtag"),
                         ((tolerant and "starttag" or "startendtag"), "randomtag",
                          [("spam", "eggs")]))
        self.assertEqual(p.get_tag(), ("endtag", "body", None))
        self.assertEqual(p.get_tag(), ("endtag", "html", None))
        self.assertRaises(NoMoreTokensError, p.get_tag)
#        print "tag", p.get_tag()
#        sys.exit()

    def test_get_text(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_get_text(pc, tolerant)
    def _test_get_text(self, parser_class, tolerant):
        from mechanize._pullparser import NoMoreTokensError
        data, f = self.data_and_file()
        p = parser_class(f)
        self.assertEqual(p.get_text(), "\n")
        self.assertEqual(peek_token(p).data, "html")
        self.assertEqual(p.get_text(), "")
        self.assertEqual(peek_token(p).data, "html"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "Title"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(),
                         "This is a data blah & a[IMG]"); p.get_token()
        self.assertEqual(p.get_text(), " & that was an entityref "
                         "and this a is\na charref.  "); p.get_token()
        self.assertEqual(p.get_text(), ".\n\n\n\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        self.assertEqual(p.get_text(), "\n"); p.get_token()
        # no more tokens, so we just get empty string
        self.assertEqual(p.get_text(), "")
        self.assertEqual(p.get_text(), "")
        self.assertRaises(NoMoreTokensError, p.get_token)
        #print "text", `p.get_text()`
        #sys.exit()

    def test_get_text_2(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_get_text_2(pc, tolerant)
    def _test_get_text_2(self, parser_class, tolerant):
        # more complicated stuff

        # endat
        data, f = self.data_and_file()
        p = parser_class(f)
        self.assertEqual(p.get_text(endat=("endtag", "html")),
                     u"\n\n\nTitle\n\n\nThis is a data blah & a[IMG]"
                     " & that was an entityref and this a is\na charref.  ."
                     "\n\n\n\n\n\n")
        f.close()

        data, f = self.data_and_file()
        p = parser_class(f)
        self.assertEqual(p.get_text(endat=("endtag", "title")),
                         "\n\n\nTitle")
        self.assertEqual(p.get_text(endat=("starttag", "img")),
                         "\n\n\nThis is a data blah & a[IMG]")
        f.close()

        # textify arg
        data, f = self.data_and_file()
        p = parser_class(f, textify={"title": "an", "img": lambda x: "YYY"})
        self.assertEqual(p.get_text(endat=("endtag", "title")),
                         "\n\n\nattr[TITLE]Title")
        self.assertEqual(p.get_text(endat=("starttag", "img")),
                         "\n\n\nThis is a data YYY")
        f.close()

        # get_compressed_text
        data, f = self.data_and_file()
        p = parser_class(f)
        self.assertEqual(p.get_compressed_text(endat=("endtag", "html")),
                         u"Title This is a data blah & a[IMG]"
                         " & that was an entityref and this a is a charref. .")
        f.close()

    def test_tags(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_tags(pc, tolerant)
    def _test_tags(self, parser_class, tolerant):
        # no args
        data, f = self.data_and_file()
        p = parser_class(f)

        expected_tag_names = [
            "html", "head", "title", "title", "head", "body", "p", "img",
            "blah", "randomtag", "body", "html"
            ]

        for i, token in enumerate(p.tags()):
            self.assertEquals(token.data, expected_tag_names[i])
        f.close()

        # tag name args
        data, f = self.data_and_file()
        p = parser_class(f)

        expected_tokens = [
            ("starttag", "head", []),
            ("endtag", "head", None),
            ("starttag", "p", []),
            ]

        for i, token in enumerate(p.tags("head", "p")):
            self.assertEquals(token, expected_tokens[i])
        f.close()

    def test_tokens(self):
        for pc, tolerant in PullParserTests.PARSERS:
            self._test_tokens(pc, tolerant)
    def _test_tokens(self, parser_class, tolerant):
        # no args
        data, f = self.data_and_file()
        p = parser_class(f)

        expected_token_types = [
            "decl", "data", "starttag", "data", "starttag", "data", "starttag",
            "data", "endtag", "data", "endtag", "data", "starttag", "data",
            "starttag", "data", "starttag", "data", "entityref", "data",
            "charref", "data", "starttag", "data", "comment", "data", "decl",
            "data", "pi", "data", (tolerant and "starttag" or "startendtag"),
            "data", "endtag", "data", "endtag", "data"
            ]

        for i, token in enumerate(p.tokens()):
            self.assertEquals(token.type, expected_token_types[i])
        f.close()

        # token type args
        data, f = self.data_and_file()
        p = parser_class(f)

        expected_tokens = [
            ("entityref", "amp", None),
            ("charref", "097", None),
            ]

        for i, token in enumerate(p.tokens("charref", "entityref")):
            self.assertEquals(token, expected_tokens[i])
        f.close()

    def test_token_eq(self):
        from mechanize._pullparser import Token
        for (a, b) in [
            (Token('endtag', 'html', None),
             ('endtag', 'html', None)),
            (Token('endtag', 'html', {'woof': 'bark'}),
             ('endtag', 'html', {'woof': 'bark'})),
            ]:
            self.assertEquals(a, a)
            self.assertEquals(a, b)
            self.assertEquals(b, a)

if __name__ == "__main__":
    import unittest
    unittest.main()
