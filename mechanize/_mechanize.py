"""Stateful programmatic WWW navigation, after Perl's WWW::Mechanize.

Copyright 2003-2004 John J. Lee <jjl@pobox.com>
Copyright 2003 Andy Lester (original Perl code)

This code is free software; you can redistribute it and/or modify it under
the terms of the BSD License (see the file COPYING included with the
distribution).

"""

# XXX
# The stuff on web page's todo list.
# Moof's emails about response object, .back(), etc.
# Add Browser.load_response() method.
# Add Browser.form_as_string() and Browser.__str__() methods.

import urlparse, re

import ClientCookie
from ClientCookie._Util import response_seek_wrapper
from ClientCookie._HeadersUtil import split_header_words
from ClientCookie._urllib2_support import HTTPRequestUpgradeProcessor
import ClientForm
import pullparser
# serves me right for not using a version tuple...
VERSION_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<bugfix>\d+)"
                        r"(?P<state>[ab])?(?:-pre)?(?P<pre>\d+)?$")
def parse_version(text):
    m = VERSION_RE.match(text)
    if m is None:
        raise ValueError
    return tuple([m.groupdict()[part] for part in
                  ("major", "minor", "bugfix", "state", "pre")])
assert map(int, parse_version(ClientCookie.VERSION)[:3]) >= [1, 0, 2], \
       "ClientCookie 1.0.2 or newer is required"
assert map(int, parse_version(ClientForm.VERSION)[:2]) >= [0, 1], \
       "ClientForm 0.1.x is required"
assert pullparser.__version__[:3] >= (0, 0, 4), \
       "pullparser 0.0.4b or newer is required"
del VERSION_RE, parse_version

from _useragent import UserAgent

__version__ = (0, 0, 9, "a", None)  # 0.0.9a

class BrowserStateError(Exception): pass
class LinkNotFoundError(Exception): pass
class FormNotFoundError(Exception): pass

class Link:
    def __init__(self, base_url, url, text, tag, attrs):
        assert None not in [url, tag, attrs]
        self.base_url = base_url
        self.absolute_url = urlparse.urljoin(base_url, url)
        self.url, self.text, self.tag, self.attrs = url, text, tag, attrs
    def __eq__(self, other):
        try:
            for name in "url", "text", "tag", "attrs":
                if getattr(self, name) != getattr(other, name):
                    return False
        except AttributeError:
            return False
        return True
    def __repr__(self):
        return "Link(base_url=%r, url=%r, text=%r, tag=%r, attrs=%r)" % (
            self.base_url, self.url, self.text, self.tag, self.attrs)

class Browser(UserAgent):
    """Browser-like class with support for history, forms and links.

    BrowserStateError is raised whenever the browser is in the wrong state to
    complete the requested operation - eg., when .back() is called when the
    browser history is empty, or when .follow_link() is called when the current
    response does not contain HTML data.

    Public attributes:

    request: last request (ClientCookie.Request or urllib2.Request)
    form: currently selected form (see .select_form())
    default_encoding: character encoding used for encoding numeric character
     references when matching link text, if no encoding is found in the reponse
     (you should turn on HTTP-EQUIV handling if you want the best chance of
     getting this right without resorting to this default)

    """
    urltags = {
        "a": "href",
        "area": "href",
        "frame": "src",
        "iframe": "src",
    }

    def __init__(self, default_encoding="latin-1"):
        self.default_encoding = default_encoding
        self._history = []  # LIFO
        self.request = self._response = None
        self.form = None
        self._forms = None
        self._title = None
        self._links = None
        UserAgent.__init__(self)  # do this last to avoid __getattr__ problems

    def close(self):
        UserAgent.close(self)
        self._history = self._forms = self._title = self._links = None
        self.request = self._response = None

    def open(self, url, data=None): return self._mech_open(url, data)

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

        if self.request is not None:
            self._history.append((self.request, self._response))
        self._response = None
        # we want self.request to be assigned even if OpenerDirector.open fails
        self.request = self._request(url, data)
        self._previous_scheme = self.request.get_type()

        self._response = ClientCookie.OpenerDirector.open(
            self, self.request, data)
        if not hasattr(self._response, "seek"):
            self._response = response_seek_wrapper(self._response)
        self._parse_html(self._response)

        return self._response

    def response(self):
        """Return last response (as return value of urllib2.urlopen())."""
        # XXX This is currently broken: responses returned by this method
        # all share the same seek position.
        return self._response

    def geturl(self):
        """Get URL of current document."""
        if self._response is None:
            raise BrowserStateError("not viewing any document")
        return self._response.geturl()

    def reload(self):
        """Reload current document, and return response object."""
        if self.request is None:
            raise BrowserStateError("no URL has yet been .open()ed")
        return self._mech_open(self.request, update_history=False)

    def back(self, n=1):
        """Go back n steps in history, and return response object.

        n: go back this number of steps (default 1 step)

        """
        while n:
            try:
                self.request, self._response = self._history.pop()
            except IndexError:
                raise BrowserStateError("already at start of history")
            n -= 1
        if self._response is not None:
            self._parse_html(self._response)
        return self._response

    def links(self, *args, **kwds):
        """Return iteratable over links (mechanize.Link objects)."""
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if args:
            raise ValueError("keyword arguments only, please!")
        if kwds:
            return self._find_links(False, **kwds)
        return self._links

    def forms(self):
        """Return iteratable over forms.

        The returned form objects implement the ClientForm.HTMLForm interface.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        return self._forms

    def viewing_html(self):
        """Return whether the current response contains HTML data."""
        if self._response is None:
            raise BrowserStateError("not viewing any document")
        ct = self._response.info().getheaders("content-type")
        return ct and ct[0].startswith("text/html")

    def title(self):
        """Return title, or None if there is no title element in the document.

        Tags are stripped or textified as described in docs for
        PullParser.get_text() method of pullparser module.

        """
        if not self.viewing_html():
            raise BrowserStateError("not viewing HTML")
        if self._title is None:
            p = pullparser.PullParser(self._response,
                                      encoding=self._encoding(self._response))
            try:
                p.get_tag("title")
            except pullparser.NoMoreTokensError:
                pass
            else:
                self._title = p.get_text()
        return self._title

    def select_form(self, name=None, predicate=None, nr=None):
        """Select an HTML form for input.

        This is like giving a form the "input focus" in a browser.

        If a form is selected, the object supports the HTMLForm interface, so
        you can call methods like .set_value(), .set(), and .click().

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
        for form in self._forms:
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

    def _add_referer_header(self, request):
        if self.request is None:
            return request
        scheme = request.get_type()
        previous_scheme = self.request.get_type()
        if scheme not in ["http", "https"]:
            return request
        request = HTTPRequestUpgradeProcessor().http_request(request)  # yuck

        if (self._handle_referer and
            previous_scheme in ["http", "https"] and not
            (previous_scheme == "https" and scheme != "https")):
            request.add_unredirected_header("Referer",
                                            self.request.get_full_url())
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
        request = ClientCookie.Request(link.absolute_url)
        return self._add_referer_header(request)

    def follow_link(self, link=None, **kwds):
        """Find a link and .open() it.

        Arguments are as for .click_link().

        """
        return self.open(self.click_link(link, **kwds))

    def find_link(self, *args, **kwds):
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
        if args:
            raise ValueError("keyword arguments only, please!")
        return self._find_links(True, **kwds)

    def __getattr__(self, name):
        # pass through ClientForm / DOMForm methods and attributes
        if self.form is not None:
            try: return getattr(self.form, name)
            except AttributeError: pass
        raise AttributeError("%s instance has no attribute %s "
                             "(perhaps you forgot to .select_form()?" %
                             (self.__class__, name))

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

        links = []
        orig_nr = nr

        for link in self._links:
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
                links.append(link)
                nr = orig_nr
        if not links:
            raise LinkNotFoundError()
        return links

    def _encoding(self, response):
        # HTTPEquivProcessor may be in use, so both HTTP and HTTP-EQUIV
        # headers may be in the response.
        ct_headers = response.info().getheaders("content-type")
        if not ct_headers:
            return self.default_encoding

        # sometimes servers return multiple HTTP headers: take the first
        http_ct = ct_headers[0]
        for k, v in split_header_words([http_ct])[0]:
            if k == "charset":
                return v

        # no HTTP-specified encoding, so look in META HTTP-EQUIV headers,
        # which, if present, will be last
        if len(ct_headers) > 1:
            equiv_ct = ct_headers[-1]
            for k, v in split_header_words([equiv_ct])[0]:
                if k == "charset":
                    return v
        return self.default_encoding

    def _parse_html(self, response):
        self.form = None
        self._title = None
        if not self.viewing_html():
            # nothing to see here
            return

        # set ._forms, ._links
        self._forms = ClientForm.ParseResponse(response)
        response.seek(0)

        base = response.geturl()

        p = pullparser.PullParser(response, encoding=self._encoding(response))
        self._links = []
        for token in p.tags(*(self.urltags.keys()+["base"])):
            if token.data == "base":
                base = dict(token.attrs).get("href")
                continue
            if token.type == "endtag":
                continue
            attrs = dict(token.attrs)
            tag = token.data
            name = attrs.get("name")
            text = None
            url = attrs.get(self.urltags[tag])
            if tag == "a":
                if token.type != "startendtag":
                    # XXX hmm, this'd break if end tag is missing
                    text = p.get_compressed_text(("endtag", tag))
                # but this doesn't work for eg. <a href="blah"><b>Andy</b></a>
                #text = p.get_compressed_text()
                # This is a hack from WWW::Mechanize to get some really basic
                # JavaScript working, which I'm not yet convinced is a good
                # idea.
##                 onClick = attrs["onclick"]
##                 m = re.search(r"/^window\.open\(\s*'([^']+)'/", onClick)
##                 if onClick and m:
##                     url = m.group(1)
            if not url:
                # Probably an <A NAME="blah"> link or <AREA NOHREF...>.
                # For our purposes a link is something with a URL, so ignore
                # this.
                continue

            link = Link(base, url, text, tag, token.attrs)
            self._links.append(link)

        response.seek(0)
