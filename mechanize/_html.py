"""HTML handling.

Copyright 2003-2006 John J. Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it under
the terms of the BSD or ZPL 2.1 licenses (see the file COPYING.txt
included with the distribution).

"""

import re, copy, urllib, htmlentitydefs
from urlparse import urljoin

import _Request
from _HeadersUtil import split_header_words, is_html as _is_html

## # XXXX miserable hack
## def urljoin(base, url):
##     if url.startswith("?"):
##         return base+url
##     else:
##         return urlparse.urljoin(base, url)

## def chr_range(a, b):
##     return "".join(map(chr, range(ord(a), ord(b)+1)))

## RESERVED_URL_CHARS = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
##                       "abcdefghijklmnopqrstuvwxyz"
##                       "-_.~")
## UNRESERVED_URL_CHARS = "!*'();:@&=+$,/?%#[]"
# we want (RESERVED_URL_CHARS+UNRESERVED_URL_CHARS), minus those
# 'safe'-by-default characters that urllib.urlquote never quotes
URLQUOTE_SAFE_URL_CHARS = "!*'();:@&=+$,/?%#[]~"

DEFAULT_ENCODING = "latin-1"

class CachingGeneratorFunction(object):
    """Caching wrapper around a no-arguments iterable."""
    def __init__(self, iterable):
        self._iterable = iterable
        self._cache = []
    def __call__(self):
        cache = self._cache
        for item in cache:
            yield item
        for item in self._iterable:
            cache.append(item)
            yield item

def encoding_finder(default_encoding):
    def encoding(response):
        # HTTPEquivProcessor may be in use, so both HTTP and HTTP-EQUIV
        # headers may be in the response.  HTTP-EQUIV headers come last,
        # so try in order from first to last.
        for ct in response.info().getheaders("content-type"):
            for k, v in split_header_words([ct])[0]:
                if k == "charset":
                    return v
        return default_encoding
    return encoding

def make_is_html(allow_xhtml):
    def is_html(response, encoding):
        ct_hdrs = response.info().getheaders("content-type")
        url = response.geturl()
        # XXX encoding
        return _is_html(ct_hdrs, url, allow_xhtml)
    return is_html

# idea for this argument-processing trick is from Peter Otten
class Args:
    def __init__(self, args_map):
        self.dictionary = dict(args_map)
    def __getattr__(self, key):
        try:
            return self.dictionary[key]
        except KeyError:
            return getattr(self.__class__, key)

def form_parser_args(
    select_default=False,
    form_parser_class=None,
    request_class=None,
    backwards_compat=False,
    ):
    return Args(locals())


class Link:
    def __init__(self, base_url, url, text, tag, attrs):
        assert None not in [url, tag, attrs]
        self.base_url = base_url
        self.absolute_url = urljoin(base_url, url)
        self.url, self.text, self.tag, self.attrs = url, text, tag, attrs
    def __cmp__(self, other):
        try:
            for name in "url", "text", "tag", "attrs":
                if getattr(self, name) != getattr(other, name):
                    return -1
        except AttributeError:
            return -1
        return 0
    def __repr__(self):
        return "Link(base_url=%r, url=%r, text=%r, tag=%r, attrs=%r)" % (
            self.base_url, self.url, self.text, self.tag, self.attrs)


def clean_url(url, encoding):
    # percent-encode illegal URL characters
    if type(url) == type(""):
        url = url.decode(encoding, "replace")
    return urllib.quote(url.encode(encoding), URLQUOTE_SAFE_URL_CHARS)

class LinksFactory:

    def __init__(self,
                 link_parser_class=None,
                 link_class=Link,
                 urltags=None,
                 ):
        import _pullparser
        if link_parser_class is None:
            link_parser_class = _pullparser.TolerantPullParser
        self.link_parser_class = link_parser_class
        self.link_class = link_class
        if urltags is None:
            urltags = {
                "a": "href",
                "area": "href",
                "frame": "src",
                "iframe": "src",
                }
        self.urltags = urltags
        self._response = None
        self._encoding = None

    def set_response(self, response, base_url, encoding):
        self._response = response
        self._encoding = encoding
        self._base_url = base_url

    def links(self):
        """Return an iterator that provides links of the document."""
        response = self._response
        encoding = self._encoding
        base_url = self._base_url
        p = self.link_parser_class(response, encoding=encoding)

        for token in p.tags(*(self.urltags.keys()+["base"])):
            if token.data == "base":
                base_url = dict(token.attrs).get("href")
                continue
            if token.type == "endtag":
                continue
            attrs = dict(token.attrs)
            tag = token.data
            name = attrs.get("name")
            text = None
            # XXX use attr_encoding for ref'd doc if that doc does not provide
            #  one by other means
            #attr_encoding = attrs.get("charset")
            url = attrs.get(self.urltags[tag])  # XXX is "" a valid URL?
            if not url:
                # Probably an <A NAME="blah"> link or <AREA NOHREF...>.
                # For our purposes a link is something with a URL, so ignore
                # this.
                continue

            url = clean_url(url, encoding)
            if tag == "a":
                if token.type != "startendtag":
                    # hmm, this'd break if end tag is missing
                    text = p.get_compressed_text(("endtag", tag))
                # but this doesn't work for eg. <a href="blah"><b>Andy</b></a>
                #text = p.get_compressed_text()

            yield Link(base_url, url, text, tag, token.attrs)

class FormsFactory:

    """Makes a sequence of objects satisfying ClientForm.HTMLForm interface.

    For constructor argument docs, see ClientForm.ParseResponse
    argument docs.

    """

    def __init__(self,
                 select_default=False,
                 form_parser_class=None,
                 request_class=None,
                 backwards_compat=False,
                 ):
        import ClientForm
        self.select_default = select_default
        if form_parser_class is None:
            form_parser_class = ClientForm.FormParser
        self.form_parser_class = form_parser_class
        if request_class is None:
            request_class = _Request.Request
        self.request_class = request_class
        self.backwards_compat = backwards_compat
        self._response = None
        self.encoding = None

    def set_response(self, response, encoding):
        self._response = response
        self.encoding = encoding

    def forms(self):
        import ClientForm
        encoding = self.encoding
        return ClientForm.ParseResponse(
            self._response,
            select_default=self.select_default,
            form_parser_class=self.form_parser_class,
            request_class=self.request_class,
            backwards_compat=self.backwards_compat,
            encoding=encoding,
            )

class TitleFactory:
    def __init__(self):
        self._response = self._encoding = None

    def set_response(self, response, encoding):
        self._response = response
        self._encoding = encoding

    def title(self):
        import _pullparser
        p = _pullparser.TolerantPullParser(
            self._response, encoding=self._encoding)
        try:
            p.get_tag("title")
        except _pullparser.NoMoreTokensError:
            return None
        else:
            return p.get_text()


def unescape(data, entities, encoding):
    if data is None or "&" not in data:
        return data

    def replace_entities(match):
        ent = match.group()
        if ent[1] == "#":
            return unescape_charref(ent[2:-1], encoding)

        repl = entities.get(ent[1:-1])
        if repl is not None:
            repl = unichr(repl)
            if type(repl) != type(""):
                try:
                    repl = repl.encode(encoding)
                except UnicodeError:
                    repl = ent
        else:
            repl = ent
        return repl

    return re.sub(r"&#?[A-Za-z0-9]+?;", replace_entities, data)

def unescape_charref(data, encoding):
    name, base = data, 10
    if name.startswith("x"):
        name, base= name[1:], 16
    uc = unichr(int(name, base))
    if encoding is None:
        return uc
    else:
        try:
            repl = uc.encode(encoding)
        except UnicodeError:
            repl = "&#%s;" % data
        return repl

def get_entitydefs():
    try:
        htmlentitydefs.name2codepoint
    except AttributeError:
        entitydefs = {}
        for name, char in htmlentitydefs.entitydefs.items():
            uc = char.decode("latin-1")
            if uc.startswith("&#") and uc.endswith(";"):
                uc = unescape_charref(uc[2:-1], None)
            codepoint = ord(uc)
            entitydefs[name] = codepoint
    else:
        entitydefs = htmlentitydefs.name2codepoint
    return entitydefs


try:
    import BeautifulSoup
except ImportError:
    pass
else:
    import sgmllib
    # monkeypatch to fix http://www.python.org/sf/803422 :-(
    sgmllib.charref = re.compile("&#(x?[0-9a-fA-F]+)[^0-9a-fA-F]")
    class MechanizeBs(BeautifulSoup.BeautifulSoup):
        _entitydefs = get_entitydefs()
        # don't want the magic Microsoft-char workaround
        PARSER_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                           lambda(x):x.group(1) + ' />'),
                          (re.compile('<!\s+([^<>]*)>'),
                           lambda(x):'<!' + x.group(1) + '>')
                          ]

        def __init__(self, encoding, text=None, avoidParserProblems=True,
                     initialTextIsEverything=True):
            self._encoding = encoding
            BeautifulSoup.BeautifulSoup.__init__(
                self, text, avoidParserProblems, initialTextIsEverything)

        def handle_charref(self, ref):
            t = unescape("&#%s;"%ref, self._entitydefs, self._encoding)
            self.handle_data(t)
        def handle_entityref(self, ref):
            t = unescape("&%s;"%ref, self._entitydefs, self._encoding)
            self.handle_data(t)
        def unescape_attrs(self, attrs):
            escaped_attrs = []
            for key, val in attrs:
                val = unescape(val, self._entitydefs, self._encoding)
                escaped_attrs.append((key, val))
            return escaped_attrs

class RobustLinksFactory:

    compress_re = re.compile(r"\s+")

    def __init__(self,
                 link_parser_class=None,
                 link_class=Link,
                 urltags=None,
                 ):
        import BeautifulSoup
        if link_parser_class is None:
            link_parser_class = MechanizeBs
        self.link_parser_class = link_parser_class
        self.link_class = link_class
        if urltags is None:
            urltags = {
                "a": "href",
                "area": "href",
                "frame": "src",
                "iframe": "src",
                }
        self.urltags = urltags
        self._bs = None
        self._encoding = None
        self._base_url = None

    def set_soup(self, soup, base_url, encoding):
        self._bs = soup
        self._base_url = base_url
        self._encoding = encoding

    def links(self):
        import BeautifulSoup
        bs = self._bs
        base_url = self._base_url
        encoding = self._encoding
        gen = bs.recursiveChildGenerator()
        for ch in bs.recursiveChildGenerator():
            if (isinstance(ch, BeautifulSoup.Tag) and
                ch.name in self.urltags.keys()+["base"]):
                link = ch
                attrs = bs.unescape_attrs(link.attrs)
                attrs_dict = dict(attrs)
                if link.name == "base":
                    base_url = attrs_dict.get("href")
                    continue
                url_attr = self.urltags[link.name]
                url = attrs_dict.get(url_attr)
                if not url:
                    continue
                url = clean_url(url, encoding)
                text = link.firstText(lambda t: True)
                if text is BeautifulSoup.Null:
                    # follow _pullparser's weird behaviour rigidly
                    if link.name == "a":
                        text = ""
                    else:
                        text = None
                else:
                    text = self.compress_re.sub(" ", text.strip())
                yield Link(base_url, url, text, link.name, attrs)


class RobustFormsFactory(FormsFactory):
    def __init__(self, *args, **kwds):
        import ClientForm
        args = form_parser_args(*args, **kwds)
        if args.form_parser_class is None:
            args.form_parser_class = ClientForm.RobustFormParser
        FormsFactory.__init__(self, **args.dictionary)

    def set_response(self, response, encoding):
        self._response = response
        self.encoding = encoding


class RobustTitleFactory:
    def __init__(self):
        self._bs = self._encoding = None

    def set_soup(self, soup, encoding):
        self._bs = soup
        self._encoding = encoding

    def title(soup):
        import BeautifulSoup
        title = self._bs.first("title")
        if title == BeautifulSoup.Null:
            return None
        else:
            return title.firstText(lambda t: True)


class Factory:
    """Factory for forms, links, etc.

    This interface may expand in future.

    Public methods:

    set_request_class(request_class)
    set_response(response)
    forms()
    links()

    Public attributes:

    encoding: string specifying the encoding of response if it contains a text
     document (this value is left unspecified for documents that do not have
     an encoding, e.g. an image file)
    is_html: true if response contains an HTML document (XHTML may be
     regarded as HTML too)
    title: page title, or None if no title or not HTML

    """

    def __init__(self, forms_factory, links_factory, title_factory,
                 get_encoding=encoding_finder(DEFAULT_ENCODING),
                 is_html_p=make_is_html(allow_xhtml=False),
                 ):
        """

        Pass keyword arguments only.

        default_encoding: character encoding to use if encoding cannot be
         determined (or guessed) from the response.  You should turn on
         HTTP-EQUIV handling if you want the best chance of getting this right
         without resorting to this default.  The default value of this
         parameter (currently latin-1) may change in future.

        """
        self._forms_factory = forms_factory
        self._links_factory = links_factory
        self._title_factory = title_factory
        self._get_encoding = get_encoding
        self._is_html_p = is_html_p

        self.set_response(None)

    def set_request_class(self, request_class):
        """Set urllib2.Request class.

        ClientForm.HTMLForm instances returned by .forms() will return
        instances of this class when .click()ed.

        """
        self._forms_factory.request_class = request_class

    def set_response(self, response):
        """Set response.

        The response must implement the same interface as objects returned by
        urllib2.urlopen().

        """
        self._response = response
        self._forms_genf = self._links_genf = None
        self._get_title = None
        for name in ["encoding", "is_html", "title"]:
            try:
                delattr(self, name)
            except AttributeError:
                pass

    def __getattr__(self, name):
        if name not in ["encoding", "is_html", "title"]:
            return getattr(self.__class__, name)

        try:
            if name == "encoding":
                self.encoding = self._get_encoding(self._response)
                return self.encoding
            elif name == "is_html":
                self.is_html = self._is_html_p(self._response, self.encoding)
                return self.is_html
            elif name == "title":
                if self.is_html:
                    self.title = self._title_factory.title()
                else:
                    self.title = None
                return self.title
        finally:
            self._response.seek(0)

    def forms(self):
        """Return iterable over ClientForm.HTMLForm-like objects."""
        if self._forms_genf is None:
            self._forms_genf = CachingGeneratorFunction(
                self._forms_factory.forms())
        return self._forms_genf()

    def links(self):
        """Return iterable over mechanize.Link-like objects."""
        if self._links_genf is None:
            self._links_genf = CachingGeneratorFunction(
                self._links_factory.links())
        return self._links_genf()

class DefaultFactory(Factory):
    """Based on sgmllib."""
    def __init__(self, i_want_broken_xhtml_support=False):
        Factory.__init__(
            self,
            forms_factory=FormsFactory(),
            links_factory=LinksFactory(),
            title_factory=TitleFactory(),
            is_html_p=make_is_html(allow_xhtml=i_want_broken_xhtml_support),
            )

    def set_response(self, response):
        Factory.set_response(self, response)
        if response is not None:
            self._forms_factory.set_response(
                copy.copy(response), self.encoding)
            self._links_factory.set_response(
                copy.copy(response), self._response.geturl(), self.encoding)
            self._title_factory.set_response(
                copy.copy(response), self.encoding)

class RobustFactory(Factory):
    """Based on BeautifulSoup, hopefully a bit more robust to bad HTML than is
    DefaultFactory.

    """
    def __init__(self, i_want_broken_xhtml_support=False,
                 soup_class=None):
        Factory.__init__(
            self,
            forms_factory=RobustFormsFactory(),
            links_factory=RobustLinksFactory(),
            title_factory=RobustTitleFactory(),
            is_html_p=make_is_html(allow_xhtml=i_want_broken_xhtml_support),
            )
        if soup_class is None:
            soup_class = MechanizeBs
        self._soup_class = soup_class

    def set_response(self, response):
        import BeautifulSoup
        Factory.set_response(self, response)
        if response is not None:
            data = response.read()
            soup = self._soup_class(self.encoding, data)
            self._forms_factory.set_response(response, self.encoding)
            self._links_factory.set_soup(
                soup, response.geturl(), self.encoding)
            self._title_factory.set_soup(soup, self.encoding)
