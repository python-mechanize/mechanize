from __future__ import generators

import re, urllib, htmlentitydefs
from urlparse import urljoin

import ClientCookie

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
    encoding="latin-1",  # deprecated
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
        import pullparser
        if link_parser_class is None:
            link_parser_class = pullparser.TolerantPullParser
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

    def links(self, fh, base_url, encoding=None):
        """Return an iterator that provides links of the document."""
        import pullparser
        p = self.link_parser_class(fh, encoding=encoding)

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
                 encoding="latin-1",  # deprecated
                 ):
        import ClientForm
        self.select_default = select_default
        if form_parser_class is None:
            form_parser_class = ClientForm.FormParser
        self.form_parser_class = form_parser_class
        if request_class is None:
            request_class = ClientCookie.Request
        self.request_class = request_class
        self.backwards_compat = backwards_compat
        self.encoding = encoding

    def parse_response(self, response, encoding=None):
        import ClientForm
        if encoding is None:
            encoding = self.encoding
        return ClientForm.ParseResponse(
            response,
            select_default=self.select_default,
            form_parser_class=self.form_parser_class,
            request_class=self.request_class,
            backwards_compat=self.backwards_compat,
            encoding=encoding,
            )

    def parse_file(self, file_obj, base_url, encoding=None):
        import ClientForm
        if encoding is None:
            encoding = self.encoding
        return ClientForm.ParseFile(
            file_obj,
            base_url,
            select_default=self.select_default,
            form_parser_class=self.form_parser_class,
            request_class=self.request_class,
            backwards_compat=self.backwards_compat,
            encoding=encoding,
            )

def pp_get_title(response, encoding):
    import pullparser
    p = pullparser.TolerantPullParser(response, encoding=encoding)
    try:
        p.get_tag("title")
    except pullparser.NoMoreTokensError:
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

    def links(self, fh, base_url, encoding=None):
        import BeautifulSoup
        data = fh.read()
        bs = self.link_parser_class(encoding, data)
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
                    # follow pullparser's weird behaviour rigidly
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

def bs_get_title(response, encoding):
    import BeautifulSoup
    # XXXX encoding
    bs = BeautifulSoup.BeautifulSoup(response.read())
    title = bs.first("title")
    if title == BeautifulSoup.Null:
        return None
    else:
        return title.firstText(lambda t: True)


class Factory:
    """Factory for forms, links, etc.

    The interface of this class may expand in future.

    """

    def __init__(self, forms_factory, links_factory, get_title):
        """

        Pass keyword
        arguments only.

        """
        self._forms_factory = forms_factory
        self._links_factory = links_factory
        self._get_title = get_title

    def set_request_class(self, request_class):
        """Set urllib2.Request class.

        ClientForm.HTMLForm instances returned by .forms() will return
        instances of this class when .click()ed.

        """
        self._forms_factory.request_class = request_class

    def forms(self, response, encoding):
        """Return iterable over ClientForm.HTMLForm-like objects."""
        return self._forms_factory.parse_response(response, encoding)

    def links(self, response, encoding):
        """Return iterable over mechanize.Link-like objects."""
        return self._links_factory.links(response, response.geturl(), encoding)

    def title(self, response, encoding):
        """Return page title."""
        return self._get_title(response, encoding)

class DefaultFactory(Factory):
    def __init__(self):
        Factory.__init__(self,
                         forms_factory=FormsFactory(),
                         links_factory=LinksFactory(),
                         get_title=pp_get_title,
                         )

class RobustFactory(Factory):
    def __init__(self):
        Factory.__init__(self,
                         forms_factory=RobustFormsFactory(),
                         links_factory=RobustLinksFactory(),
                         get_title=bs_get_title,
                         )
