"""Stateful programmatic WWW navigation, after Perl's WWW::Mechanize.

Copyright 2003-2006 John J. Lee <jjl@pobox.com>
Copyright 2003 Andy Lester (original Perl code)

This code is free software; you can redistribute it and/or modify it under
the terms of the BSD License (see the file COPYING included with the
distribution).

"""

# XXXX
# test referer bugs (frags and don't add in redirect unless orig req had Referer)

# XXX
# The stuff on web page's todo list.
# Moof's emails about response object, .back(), etc.

from __future__ import generators

import urllib2, socket, urlparse, urllib, re, sys, htmlentitydefs, copy
from urlparse import urljoin

import ClientCookie
from ClientCookie._Util import response_seek_wrapper
from ClientCookie._HeadersUtil import split_header_words, is_html

from _useragent import UserAgent

__version__ = (0, 0, 12, "a", None)  # 0.0.12a

class BrowserStateError(Exception): pass
class LinkNotFoundError(Exception): pass
class FormNotFoundError(Exception): pass

## def chr_range(a, b):
##     return "".join(map(chr, range(ord(a), ord(b)+1)))

## RESERVED_URL_CHARS = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
##                       "abcdefghijklmnopqrstuvwxyz"
##                       "-_.~")
## UNRESERVED_URL_CHARS = "!*'();:@&=+$,/?%#[]"
# we want (RESERVED_URL_CHARS+UNRESERVED_URL_CHARS), minus those
# 'safe'-by-default characters that urllib.urlquote never quotes
URLQUOTE_SAFE_URL_CHARS = "!*'();:@&=+$,/?%#[]~"

## # XXXX miserable hack
## def urljoin(base, url):
##     if url.startswith("?"):
##         return base+url
##     else:
##         return urlparse.urljoin(base, url)

# idea for this argument-processing trick is from Peter Otten
class Args:
    def __init__(self):
        self._args = {}
    def add_arg(self, name, value):
        self._args[name] = value
    def __getattr__(self, key):
        try:
            return self._args[key]
        except KeyError:
            return getattr(self.__class__, key)
    def dictionary(self):
        return self._args
def get_args(d):
    args = Args()
    for n, v in d.iteritems():
        args.add_arg(n, v)
    return args

def form_parser_args(
    select_default=False,
    form_parser_class=None,
    request_class=None,
    backwards_compat=False,
    encoding="latin-1",  # deprecated
    ):
    return get_args(locals())


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


def cleanUrl(url, encoding):
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

            url = cleanUrl(url, encoding)
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

    return re.sub(r"&#?\S+?;", replace_entities, data)

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
                if type(url) == type(""):
                    url = url.decode(encoding, "replace")
                url = urllib.quote(url.encode(encoding), URLQUOTE_SAFE_URL_CHARS)
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
        FormsFactory.__init__(self, **args.dictionary())

def bs_get_title(response, encoding):
    import BeautifulSoup
    # XXXX encoding
    bs = BeautifulSoup.BeautifulSoup(response.read())
    title = bs.first("title")
    if title == BeautifulSoup.Null:
        return None
    else:
        return bs.firstText(lambda t: True)


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


class History:
    def __init__(self):
        self._history = []  # LIFO
    def add(self, request, response):
        self._history.append((request, response))
    def back(self, n, _response):
        response = _response  # XXX move Browser._response into this class?
        while n > 0 or response is None:
            try:
                request, response = self._history.pop()
            except IndexError:
                raise BrowserStateError("already at start of history")
            n -= 1
        return request, response
    def clear(self):
        del self._history[:]
    def close(self):
        for request, response in self._history:
            response.close()
        del self._history[:]


if sys.version_info[:2] >= (2, 4):
    from ClientCookie._Opener import OpenerMixin
else:
    class OpenerMixin: pass

class Browser(UserAgent, OpenerMixin):
    """Browser-like class with support for history, forms and links.

    BrowserStateError is raised whenever the browser is in the wrong state to
    complete the requested operation - eg., when .back() is called when the
    browser history is empty, or when .follow_link() is called when the current
    response does not contain HTML data.

    Public attributes:

    request: last request (ClientCookie.Request or urllib2.Request)
    form: currently selected form (see .select_form())
    default_encoding: character encoding used if no encoding is found in the
     response (you should turn on HTTP-EQUIV handling if you want the best
     chance of getting this right without resorting to this default)

    """

    def __init__(self, default_encoding="latin-1",
                 factory=None,
                 history=None,
                 request_class=None,
                 forms_factory=None,  # deprecated
                 links_factory=None,  # deprecated
                 get_title=None,  # deprecated
                 ):
        """

        Only named arguments should be passed to this constructor.

        default_encoding: See class docs.
        request_class: Request class to use.  Defaults to ClientCookie.Request
         by default for Pythons older than 2.4, urllib2.Request otherwise.
        factory: mechanize.Factory

        Note that the supplied factory's request_class is overridden by this
        constructor, to ensure only one Request class is used.


        Deprecated arguments:

        forms_factory: Object supporting the mechanize.FormsFactory interface.
        links_factory: Object supporting the mechanize.LinksFactory interface.
        get_title: callable taking a response object and an encoding string,
         and returning the page title.

        """
        self.default_encoding = default_encoding
        if history is None:
            history = History()
        self._history = history
        self.request = self._response = None
        self.form = None
        self._forms = None
        self._links = None
        self._title = None

        if request_class is None:
            if not hasattr(urllib2.Request, "add_unredirected_header"):
                request_class = ClientCookie.Request
            else:
                request_class = urllib2.Request  # Python 2.4

        if factory is None:
            if (forms_factory is None and
                links_factory is None and
                get_title is None):
                factory = DefaultFactory()
            else:
                factory = Factory(forms_factory, links_factory, get_title)
        factory.set_request_class(request_class)
        self._factory = factory
        self.request_class = request_class

        UserAgent.__init__(self)  # do this last to avoid __getattr__ problems

    def close(self):
        if self._response is not None:
            self._response.close()    
        UserAgent.close(self)
        if self._history is not None:
            self._history.close()
            self._history = None
        self._forms = self._title = self._links = None
        self.request = self._response = None

    def open(self, url, data=None):
        if self._response is not None:
            self._response.close()
        return self._mech_open(url, data)

    def _mech_open(self, url, data=None, update_history=True):
        try:
            url.get_full_url
        except AttributeError:
            # string URL -- convert to absolute URL if required
            scheme, netloc = urlparse.urlparse(url)[:2]
            if not scheme:
                # relative URL
                assert not netloc, "malformed URL"
                if self._response is None:
                    raise BrowserStateError(
                        "can't fetch relative URL: not viewing any document")
                url = urlparse.urljoin(self._response.geturl(), url)

        if self.request is not None and update_history:
            self._history.add(self.request, self._response)
        self._response = None
        # we want self.request to be assigned even if UserAgent.open fails
        self.request = self._request(url, data)
        self._previous_scheme = self.request.get_type()

        success = True
        try:
            self._response = UserAgent.open(self, self.request, data)
        except urllib2.URLError, error:
            success = False
            self._response = error
        except (IOError, socket.error, OSError), error:
            # Yes, urllib2 really does raise all these :-((
            # I don't want to start fixing these here, though, since this is a
            # subclass of OpenerDirector, and it would break old code.  Even in
            # Python core, a fix would need some backwards-compat. hack to be
            # acceptable.
            raise
        if not hasattr(self._response, "seek"):
            self._response = response_seek_wrapper(self._response)
        self._parse_html(self._response)
        if not success:
            raise error
        return copy.copy(self._response)

    def response(self):
        """Return last response (as return value of urllib2.urlopen())."""
        return copy.copy(self._response)

    def geturl(self):
        """Get URL of current document."""
        if self._response is None:
            raise BrowserStateError("not viewing any document")
        return self._response.geturl()

    def reload(self):
        """Reload current document, and return response object."""
        if self.request is None:
            raise BrowserStateError("no URL has yet been .open()ed")
        if self._response is not None:
            self._response.close()
        return self._mech_open(self.request, update_history=False)

    def back(self, n=1):
        """Go back n steps in history, and return response object.

        n: go back this number of steps (default 1 step)

        """
        if self._response is not None:
            self._response.close()
        self.request, self._response = self._history.back(n, self._response)
        self._parse_html(self._response)
        return self._response

    def clear_history(self):
        self._history.clear()

    def links(self, **kwds):
        """Return iterable over links (mechanize.Link objects)."""
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if kwds:
            return self._find_links(False, **kwds)
        if self._links is None:
            try:
                self._links = list(self.get_links_iter())
            finally:
                self._response.seek(0)
        return self._links

    def get_links_iter(self):
        """Return an iterator that provides links of the document.

        This method is provided in addition to .links() to allow lazy iteration
        over links, while still keeping .links() safe against somebody
        .seek()ing on a response "behind your back".  When response objects are
        fixed to have independent seek positions, this method will be
        deprecated in favour of .links().

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        base_url = self._response.geturl()
        self._response.seek(0)
        return self._factory.links(
            self._response, self._encoding(self._response))

    def forms(self):
        """Return iterable over forms.

        The returned form objects implement the ClientForm.HTMLForm interface.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if self._forms is None:
            response = self._response
            response.seek(0)
            try:
                self._forms = self._factory.forms(
                    response, self._encoding(self._response))
            finally:
                response.seek(0)
        return self._forms

    def viewing_html(self):
        """Return whether the current response contains HTML data."""
        if self._response is None:
            raise BrowserStateError("not viewing any document")
        ct_hdrs = self._response.info().getheaders("content-type")
        url = self._response.geturl()
        return is_html(ct_hdrs, url)

    def title(self):
        """Return title, or None if there is no title element in the document.

        Tags are stripped or textified as described in docs for
        PullParser.get_text() method of pullparser module.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if self._title is None:
            self._title = self._factory.title(
                self._response, self._encoding(self._response))
        return self._title

    def select_form(self, name=None, predicate=None, nr=None):
        """Select an HTML form for input.

        This is a bit like giving a form the "input focus" in a browser.

        If a form is selected, the Browser object supports the HTMLForm
        interface, so you can call methods like .set_value(), .set(), and
        .click().

        At least one of the name, predicate and nr arguments must be supplied.
        If no matching form is found, mechanize.FormNotFoundError is raised.

        If name is specified, then the form must have the indicated name.

        If predicate is specified, then the form must match that function.  The
        predicate function is passed the HTMLForm as its single argument, and
        should return a boolean value indicating whether the form matched.

        nr, if supplied, is the sequence number of the form (where 0 is the
        first).  Note that control 0 is the first form matching all the other
        arguments (if supplied); it is not necessarily the first control in the
        form.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if (name is None) and (predicate is None) and (nr is None):
            raise ValueError(
                "at least one argument must be supplied to specify form")

        orig_nr = nr
        for form in self.forms():
            if name is not None and name != form.name:
                continue
            if predicate is not None and not predicate(form):
                continue
            if nr:
                nr -= 1
                continue
            self.form = form
            break  # success
        else:
            # failure
            description = []
            if name is not None: description.append("name '%s'" % name)
            if predicate is not None:
                description.append("predicate %s" % predicate)
            if orig_nr is not None: description.append("nr %d" % orig_nr)
            description = ", ".join(description)
            raise FormNotFoundError("no form matching "+description)

    def _add_referer_header(self, request, origin_request=True):
        if self.request is None:
            return request
        scheme = request.get_type()
        original_scheme = self.request.get_type()
        if scheme not in ["http", "https"]:
            return request
        if not origin_request and not self.request.has_header("Referer"):
            return request

        if (self._handle_referer and
            original_scheme in ["http", "https"] and
            not (original_scheme == "https" and scheme != "https")):
            # strip URL fragment (RFC 2616 14.36)
            parts = urlparse.urlparse(self.request.get_full_url())
            parts = parts[:-1]+("",)
            referer = urlparse.urlunparse(parts)
            request.add_unredirected_header("Referer", referer)
        return request

    def click(self, *args, **kwds):
        """See ClientForm.HTMLForm.click for documentation."""
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        request = self.form.click(*args, **kwds)
        return self._add_referer_header(request)

    def submit(self, *args, **kwds):
        """Submit current form.

        Arguments are as for ClientForm.HTMLForm.click().

        Return value is same as for Browser.open().

        """
        return self.open(self.click(*args, **kwds))

    def click_link(self, link=None, **kwds):
        """Find a link and return a Request object for it.

        Arguments are as for .find_link(), except that a link may be supplied
        as the first argument.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if not link:
            link = self.find_link(**kwds)
        else:
            if kwds:
                raise ValueError(
                    "either pass a Link, or keyword arguments, not both")
        request = self.request_class(link.absolute_url)
        return self._add_referer_header(request)

    def follow_link(self, link=None, **kwds):
        """Find a link and .open() it.

        Arguments are as for .click_link().

        Return value is same as for Browser.open().

        """
        return self.open(self.click_link(link, **kwds))

    def find_link(self, **kwds):
        """Find a link in current page.

        Links are returned as mechanize.Link objects.

        # Return third link that .search()-matches the regexp "python"
        # (by ".search()-matches", I mean that the regular expression method
        # .search() is used, rather than .match()).
        find_link(text_regex=re.compile("python"), nr=2)

        # Return first http link in the current page that points to somewhere
        # on python.org whose link text (after tags have been removed) is
        # exactly "monty python".
        find_link(text="monty python",
                  url_regex=re.compile("http.*python.org"))

        # Return first link with exactly three HTML attributes.
        find_link(predicate=lambda link: len(link.attrs) == 3)

        Links include anchors (<a>), image maps (<area>), and frames (<frame>,
        <iframe>).

        All arguments must be passed by keyword, not position.  Zero or more
        arguments may be supplied.  In order to find a link, all arguments
        supplied must match.

        If a matching link is not found, mechanize.LinkNotFoundError is raised.

        text: link text between link tags: eg. <a href="blah">this bit</a> (as
         returned by pullparser.get_compressed_text(), ie. without tags but
         with opening tags "textified" as per the pullparser docs) must compare
         equal to this argument, if supplied
        text_regex: link text between tag (as defined above) must match the
         regular expression object passed as this argument, if supplied
        name, name_regex: as for text and text_regex, but matched against the
         name HTML attribute of the link tag
        url, url_regex: as for text and text_regex, but matched against the
         URL of the link tag (note this matches against Link.url, which is a
         relative or absolute URL according to how it was written in the HTML)
        tag: element name of opening tag, eg. "a"
        predicate: a function taking a Link object as its single argument,
         returning a boolean result, indicating whether the links
        nr: matches the nth link that matches all other criteria (default 0)

        """
        return self._find_links(True, **kwds)

    def __getattr__(self, name):
        # pass through ClientForm / DOMForm methods and attributes
        form = self.__dict__.get("form")
        if form is None:
            raise AttributeError(
                "%s instance has no attribute %s (perhaps you forgot to "
                ".select_form()?)" % (self.__class__, name))
        return getattr(form, name)

#---------------------------------------------------
# Private methods.

    def _find_links(self, single,
                    text=None, text_regex=None,
                    name=None, name_regex=None,
                    url=None, url_regex=None,
                    tag=None,
                    predicate=None,
                    nr=0
                    ):
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")

        found_links = []
        orig_nr = nr

        # An optimization, so that if we look for a single link we do not have
        # to necessarily parse the entire file.
        if self._links is None and single:
            all_links = self.get_links_iter()
        else:
            if self._links is None:
                try:
                    self._links = list(self.get_links_iter())
                finally:
                    self._response.seek(0)
            all_links = self._links

        for link in all_links:
            if url is not None and url != link.url:
                continue
            if url_regex is not None and not url_regex.search(link.url):
                continue
            if (text is not None and
                (link.text is None or text != link.text)):
                continue
            if (text_regex is not None and
                (link.text is None or not text_regex.search(link.text))):
                continue
            if name is not None and name != dict(link.attrs).get("name"):
                continue
            if name_regex is not None:
                link_name = dict(link.attrs).get("name")
                if link_name is None or not name_regex.search(link_name):
                    continue
            if tag is not None and tag != link.tag:
                continue
            if predicate is not None and not predicate(link):
                continue
            if nr:
                nr -= 1
                continue
            if single:
                return link
            else:
                found_links.append(link)
                nr = orig_nr
        if not found_links:
            raise LinkNotFoundError()
        return found_links

    def _encoding(self, response):
        # HTTPEquivProcessor may be in use, so both HTTP and HTTP-EQUIV
        # headers may be in the response.  HTTP-EQUIV headers come last,
        # so try in order from first to last.
        for ct in response.info().getheaders("content-type"):
            for k, v in split_header_words([ct])[0]:
                if k == "charset":
                    return v
        return self.default_encoding

    def _parse_html(self, response):
        # this is now lazy, so we just reset the various attributes that
        # result from parsing
        self.form = None
        self._title = None
        self._forms = self._links = None
