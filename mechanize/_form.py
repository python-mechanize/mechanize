"""HTML form handling for web clients.

HTML form handling for web clients: useful for parsing HTML forms, filling them
in and returning the completed forms to the server.  This code developed from a
port of Gisle Aas' Perl module HTML::Form, from the libwww-perl library, but
the interface is not the same.

The most useful docstring is the one for HTMLForm.

RFC 1866: HTML 2.0
RFC 1867: Form-based File Upload in HTML
RFC 2388: Returning Values from Forms: multipart/form-data
HTML 3.2 Specification, W3C Recommendation 14 January 1997 (for ISINDEX)
HTML 4.01 Specification, W3C Recommendation 24 December 1999


Copyright 2002-2007 John J. Lee <jjl@pobox.com>
Copyright 2005 Gary Poster
Copyright 2005 Zope Corporation
Copyright 1998-2000 Gisle Aas.

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

# TODO:
# Clean up post the merge into mechanize
#  * Remove code that was duplicated in ClientForm and mechanize
#  * Remove weird import stuff
#  * Remove pre-Python 2.4 compatibility cruft
#  * Clean up tests
#  * Later release: Remove the ClientForm 0.1 backwards-compatibility switch
# Remove parser testing hack
# Clean action URI
# Switch to unicode throughout
#  See Wichert Akkerman's 2004-01-22 message to c.l.py.
# Apply recommendations from google code project CURLIES
# Apply recommendations from HTML 5 spec
# Add charset parameter to Content-type headers?  How to find value??
# Functional tests to add:
#  Single and multiple file upload
#  File upload with missing name (check standards)
# mailto: submission & enctype text/plain??

# Replace by_label etc. with moniker / selector concept.  Allows, e.g., a
#  choice between selection by value / id / label / element contents.  Or
#  choice between matching labels exactly or by substring.  etc.

__all__ = [
    'AmbiguityError', 'CheckboxControl', 'Control', 'ControlNotFoundError',
    'FileControl', 'FormParser', 'HTMLForm', 'HiddenControl', 'IgnoreControl',
    'ImageControl', 'IsindexControl', 'Item', 'ItemCountError',
    'ItemNotFoundError', 'Label', 'ListControl', 'LocateError', 'Missing',
    'ParseError', 'ParseFile', 'ParseFileEx', 'ParseResponse',
    'ParseResponseEx', 'PasswordControl', 'RadioControl', 'ScalarControl',
    'SelectControl', 'SubmitButtonControl', 'SubmitControl', 'TextControl',
    'TextareaControl', 'XHTMLCompatibleFormParser', 'choose_boundary'
]

import HTMLParser
import inspect
import logging
import re
# from Python itself, for backwards compatibility of raised exceptions
import sgmllib
import sys
import urlparse
from cStringIO import StringIO

import _beautifulsoup
import _request
# bundled copy of sgmllib
import _sgmllib_copy
from _form_controls import (
    AmbiguityError, CheckboxControl, Control, ControlNotFoundError,
    FileControl, HiddenControl, HTMLForm, IgnoreControl, ImageControl,
    IsindexControl, Item, ItemCountError, ItemNotFoundError, Label,
    ListControl, LocateError, Missing, PasswordControl, RadioControl,
    ScalarControl, SelectControl, SubmitButtonControl, SubmitControl,
    TextareaControl, TextControl, choose_boundary, deprecation)

VERSION = "0.2.11"

CHUNK = 1024  # size of chunks fed to parser, in bytes

DEFAULT_ENCODING = "latin-1"

_logger = logging.getLogger("mechanize.forms")
OPTIMIZATION_HACK = True


def debug(msg, *args, **kwds):
    if OPTIMIZATION_HACK:
        return

    caller_name = inspect.stack()[1][3]
    extended_msg = '%%s %s' % msg
    extended_args = (caller_name, ) + args
    _logger.debug(extended_msg, *extended_args, **kwds)


def _show_debug_messages():
    global OPTIMIZATION_HACK
    OPTIMIZATION_HACK = False
    _logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    _logger.addHandler(handler)


def normalize_line_endings(text):
    return re.sub(r"(?:(?<!\r)\n)|(?:\r(?!\n))", "\r\n", text)


def unescape(data, entities, encoding=DEFAULT_ENCODING):
    if data is None or "&" not in data:
        return data

    def replace_entities(match, entities=entities, encoding=encoding):
        ent = match.group()
        if ent[1] == "#":
            return unescape_charref(ent[2:-1], encoding)

        repl = entities.get(ent)
        if repl is not None:
            if type(repl) != type(""):  # noqa
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
        name, base = name[1:], 16
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
    import htmlentitydefs
    from codecs import latin_1_decode
    entitydefs = {}
    try:
        htmlentitydefs.name2codepoint
    except AttributeError:
        entitydefs = {}
        for name, char in htmlentitydefs.entitydefs.items():
            uc = latin_1_decode(char)[0]
            if uc.startswith("&#") and uc.endswith(";"):
                uc = unescape_charref(uc[2:-1], None)
            entitydefs["&%s;" % name] = uc
    else:
        for name, codepoint in htmlentitydefs.name2codepoint.items():
            entitydefs["&%s;" % name] = unichr(codepoint)
    return entitydefs


def issequence(x):
    try:
        x[0]
    except (TypeError, KeyError):
        return False
    except IndexError:
        pass
    return True


# for backwards compatibility, ParseError derives from exceptions that were
# raised by versions of ClientForm <= 0.2.5
# TODO: move to _html
class ParseError(sgmllib.SGMLParseError, HTMLParser.HTMLParseError):

    def __init__(self, *args, **kwds):
        Exception.__init__(self, *args, **kwds)

    def __str__(self):
        return Exception.__str__(self)


class _AbstractFormParser:
    """forms attribute contains HTMLForm instances on completion."""

    # thanks to Moshe Zadka for an example of sgmllib/htmllib usage
    def __init__(self, entitydefs=None, encoding=DEFAULT_ENCODING):
        if entitydefs is None:
            entitydefs = get_entitydefs()
        self._entitydefs = entitydefs
        self._encoding = encoding

        self.base = None
        self.forms = []
        self.labels = []
        self._current_label = None
        self._current_form = None
        self._select = None
        self._optgroup = None
        self._option = None
        self._textarea = None

        # forms[0] will contain all controls that are outside of any form
        # self._global_form is an alias for self.forms[0]
        self._global_form = None
        self.start_form([])
        self.end_form()
        self._current_form = self._global_form = self.forms[0]

    def do_base(self, attrs):
        debug("%s", attrs)
        for key, value in attrs:
            if key == "href":
                self.base = self.unescape_attr_if_required(value)

    def end_body(self):
        debug("")
        if self._current_label is not None:
            self.end_label()
        if self._current_form is not self._global_form:
            self.end_form()

    def start_form(self, attrs):
        debug("%s", attrs)
        if self._current_form is not self._global_form:
            raise ParseError("nested FORMs")
        name = None
        action = None
        enctype = "application/x-www-form-urlencoded"
        method = "GET"
        d = {}
        for key, value in attrs:
            if key == "name":
                name = self.unescape_attr_if_required(value)
            elif key == "action":
                action = self.unescape_attr_if_required(value)
            elif key == "method":
                method = self.unescape_attr_if_required(value.upper())
            elif key == "enctype":
                enctype = self.unescape_attr_if_required(value.lower())
            d[key] = self.unescape_attr_if_required(value)
        controls = []
        self._current_form = (name, action, method, enctype), d, controls

    def end_form(self):
        debug("")
        if self._current_label is not None:
            self.end_label()
        if self._current_form is self._global_form:
            raise ParseError("end of FORM before start")
        self.forms.append(self._current_form)
        self._current_form = self._global_form

    def start_select(self, attrs):
        debug("%s", attrs)
        if self._select is not None:
            raise ParseError("nested SELECTs")
        if self._textarea is not None:
            raise ParseError("SELECT inside TEXTAREA")
        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)

        self._select = d
        self._add_label(d)

        self._append_select_control({"__select": d})

    def end_select(self):
        debug("")
        if self._select is None:
            raise ParseError("end of SELECT before start")

        if self._option is not None:
            self._end_option()

        self._select = None

    def start_optgroup(self, attrs):
        debug("%s", attrs)
        if self._select is None:
            raise ParseError("OPTGROUP outside of SELECT")
        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)

        self._optgroup = d

    def end_optgroup(self):
        debug("")
        if self._optgroup is None:
            raise ParseError("end of OPTGROUP before start")
        self._optgroup = None

    def _start_option(self, attrs):
        debug("%s", attrs)
        if self._select is None:
            raise ParseError("OPTION outside of SELECT")
        if self._option is not None:
            self._end_option()

        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)

        self._option = {}
        self._option.update(d)
        if (self._optgroup and 'disabled' in self._optgroup and
                'disabled' not in self._option):
            self._option["disabled"] = None

    def _end_option(self):
        debug("")
        if self._option is None:
            raise ParseError("end of OPTION before start")

        contents = self._option.get("contents", "").strip()
        self._option["contents"] = contents
        if 'value' not in self._option:
            self._option["value"] = contents
        if 'label' not in self._option:
            self._option["label"] = contents
        # stuff dict of SELECT HTML attrs into a special private key
        #  (gets deleted again later)
        self._option["__select"] = self._select
        self._append_select_control(self._option)
        self._option = None

    def _append_select_control(self, attrs):
        debug("%s", attrs)
        controls = self._current_form[2]
        name = self._select.get("name")
        controls.append(("select", name, attrs))

    def start_textarea(self, attrs):
        debug("%s", attrs)
        if self._textarea is not None:
            raise ParseError("nested TEXTAREAs")
        if self._select is not None:
            raise ParseError("TEXTAREA inside SELECT")
        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)
        self._add_label(d)

        self._textarea = d

    def end_textarea(self):
        debug("")
        if self._textarea is None:
            raise ParseError("end of TEXTAREA before start")
        controls = self._current_form[2]
        name = self._textarea.get("name")
        controls.append(("textarea", name, self._textarea))
        self._textarea = None

    def start_label(self, attrs):
        debug("%s", attrs)
        if self._current_label:
            self.end_label()
        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)
        taken = bool(d.get("for"))  # empty id is invalid
        d["__text"] = ""
        d["__taken"] = taken
        if taken:
            self.labels.append(d)
        self._current_label = d

    def end_label(self):
        debug("")
        label = self._current_label
        if label is None:
            # something is ugly in the HTML, but we're ignoring it
            return
        self._current_label = None
        # if it is staying around, it is True in all cases
        del label["__taken"]

    def _add_label(self, d):
        # debug("%s", d)
        if self._current_label is not None:
            if not self._current_label["__taken"]:
                self._current_label["__taken"] = True
                d["__label"] = self._current_label

    def handle_data(self, data):
        debug("%s", data)

        if self._option is not None:
            # self._option is a dictionary of the OPTION element's HTML
            # attributes, but it has two special keys, one of which is the
            # special "contents" key contains text between OPTION tags (the
            # other is the "__select" key: see the end_option method)
            map = self._option
            key = "contents"
        elif self._textarea is not None:
            map = self._textarea
            key = "value"
            data = normalize_line_endings(data)
        # not if within option or textarea
        elif self._current_label is not None:
            map = self._current_label
            key = "__text"
        else:
            return

        if data and key not in map:
            # according to
            # http://www.w3.org/TR/html4/appendix/notes.html#h-B.3.1 line break
            # immediately after start tags or immediately before end tags must
            # be ignored, but real browsers only ignore a line break after a
            # start tag, so we'll do that.
            if data[0:2] == "\r\n":
                data = data[2:]
            elif data[0:1] in ["\n", "\r"]:
                data = data[1:]
            map[key] = data
        else:
            map[key] = map[key] + data

    def do_button(self, attrs):
        debug("%s", attrs)
        d = {}
        d["type"] = "submit"  # default
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)
        controls = self._current_form[2]

        type = d["type"]
        name = d.get("name")
        # we don't want to lose information, so use a type string that
        # doesn't clash with INPUT TYPE={SUBMIT,RESET,BUTTON}
        # e.g. type for BUTTON/RESET is "resetbutton"
        #     (type for INPUT/RESET is "reset")
        type = type + "button"
        self._add_label(d)
        controls.append((type, name, d))

    def do_input(self, attrs):
        debug("%s", attrs)
        d = {}
        d["type"] = "text"  # default
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)
        controls = self._current_form[2]

        type = d["type"]
        name = d.get("name")
        self._add_label(d)
        controls.append((type, name, d))

    def do_isindex(self, attrs):
        debug("%s", attrs)
        d = {}
        for key, val in attrs:
            d[key] = self.unescape_attr_if_required(val)
        controls = self._current_form[2]

        self._add_label(d)
        # isindex doesn't have type or name HTML attributes
        controls.append(("isindex", None, d))

    def handle_entityref(self, name):
        # debug("%s", name)
        self.handle_data(
            unescape('&%s;' % name, self._entitydefs, self._encoding))

    def handle_charref(self, name):
        # debug("%s", name)
        self.handle_data(unescape_charref(name, self._encoding))

    def unescape_attr(self, name):
        # debug("%s", name)
        return unescape(name, self._entitydefs, self._encoding)

    def unescape_attrs(self, attrs):
        # debug("%s", attrs)
        escaped_attrs = {}
        for key, val in attrs.items():
            try:
                val.items
            except AttributeError:
                escaped_attrs[key] = self.unescape_attr(val)
            else:
                # e.g. "__select" -- yuck!
                escaped_attrs[key] = self.unescape_attrs(val)
        return escaped_attrs

    def unknown_entityref(self, ref):
        self.handle_data("&%s;" % ref)

    def unknown_charref(self, ref):
        self.handle_data("&#%s;" % ref)


class XHTMLCompatibleFormParser(_AbstractFormParser, HTMLParser.HTMLParser):
    """Good for XHTML, bad for tolerance of incorrect HTML."""

    # thanks to Michael Howitz for this!
    def __init__(self, entitydefs=None, encoding=DEFAULT_ENCODING):
        HTMLParser.HTMLParser.__init__(self)
        _AbstractFormParser.__init__(self, entitydefs, encoding)

    def feed(self, data):
        try:
            HTMLParser.HTMLParser.feed(self, data)
        except HTMLParser.HTMLParseError, exc:
            raise ParseError(exc)

    def start_option(self, attrs):
        _AbstractFormParser._start_option(self, attrs)

    def end_option(self):
        _AbstractFormParser._end_option(self)

    def handle_starttag(self, tag, attrs):
        try:
            method = getattr(self, "start_" + tag)
        except AttributeError:
            try:
                method = getattr(self, "do_" + tag)
            except AttributeError:
                pass  # unknown tag
            else:
                method(attrs)
        else:
            method(attrs)

    def handle_endtag(self, tag):
        try:
            method = getattr(self, "end_" + tag)
        except AttributeError:
            pass  # unknown tag
        else:
            method()

    def unescape(self, name):
        # Use the entitydefs passed into constructor, not
        # HTMLParser.HTMLParser's entitydefs.
        return self.unescape_attr(name)

    def unescape_attr_if_required(self, name):
        return name  # HTMLParser.HTMLParser already did it

    def unescape_attrs_if_required(self, attrs):
        return attrs  # ditto

    def close(self):
        HTMLParser.HTMLParser.close(self)
        self.end_body()


class _AbstractSgmllibParser(_AbstractFormParser):

    def do_option(self, attrs):
        _AbstractFormParser._start_option(self, attrs)

    # we override this attr to decode hex charrefs
    entity_or_charref = re.compile(
        '&(?:([a-zA-Z][-.a-zA-Z0-9]*)|#(x?[0-9a-fA-F]+))(;?)')

    def convert_entityref(self, name):
        return unescape("&%s;" % name, self._entitydefs, self._encoding)

    def convert_charref(self, name):
        return unescape_charref("%s" % name, self._encoding)

    def unescape_attr_if_required(self, name):
        return name  # sgmllib already did it

    def unescape_attrs_if_required(self, attrs):
        return attrs  # ditto


class FormParser(_AbstractSgmllibParser, _sgmllib_copy.SGMLParser):
    """Good for tolerance of incorrect HTML, bad for XHTML."""

    def __init__(self, entitydefs=None, encoding=DEFAULT_ENCODING):
        _sgmllib_copy.SGMLParser.__init__(self)
        _AbstractFormParser.__init__(self, entitydefs, encoding)

    def feed(self, data):
        try:
            _sgmllib_copy.SGMLParser.feed(self, data)
        except _sgmllib_copy.SGMLParseError, exc:
            raise ParseError(exc)

    def close(self):
        _sgmllib_copy.SGMLParser.close(self)
        self.end_body()


class _AbstractBSFormParser(_AbstractSgmllibParser):

    bs_base_class = None

    def __init__(self, entitydefs=None, encoding=DEFAULT_ENCODING):
        _AbstractFormParser.__init__(self, entitydefs, encoding)
        self.bs_base_class.__init__(self)

    def handle_data(self, data):
        _AbstractFormParser.handle_data(self, data)
        self.bs_base_class.handle_data(self, data)

    def feed(self, data):
        try:
            self.bs_base_class.feed(self, data)
        except _sgmllib_copy.SGMLParseError, exc:
            raise ParseError(exc)

    def close(self):
        self.bs_base_class.close(self)
        self.end_body()


class RobustFormParser(_AbstractBSFormParser, _beautifulsoup.BeautifulSoup):
    """Tries to be highly tolerant of incorrect HTML."""

    bs_base_class = _beautifulsoup.BeautifulSoup


class NestingRobustFormParser(_AbstractBSFormParser,
                              _beautifulsoup.ICantBelieveItsBeautifulSoup):
    """Tries to be highly tolerant of incorrect HTML.

    Different from RobustFormParser in that it more often guesses nesting
    above missing end tags (see BeautifulSoup docs).
    """

    bs_base_class = _beautifulsoup.ICantBelieveItsBeautifulSoup


def ParseResponseEx(
        response,
        select_default=False,
        form_parser_class=FormParser,
        request_class=_request.Request,
        entitydefs=None,
        encoding=DEFAULT_ENCODING,

        # private
        _urljoin=urlparse.urljoin,
        _urlparse=urlparse.urlparse,
        _urlunparse=urlparse.urlunparse, ):
    """Identical to ParseResponse, except that:

    1. The returned list contains an extra item.  The first form in the list
    contains all controls not contained in any FORM element.

    2. The arguments ignore_errors and backwards_compat have been removed.

    3. Backwards-compatibility mode (backwards_compat=True) is not available.
    """
    return _ParseFileEx(
        response,
        response.geturl(),
        select_default,
        False,
        form_parser_class,
        request_class,
        entitydefs,
        False,
        encoding,
        _urljoin=_urljoin,
        _urlparse=_urlparse,
        _urlunparse=_urlunparse, )


def ParseFileEx(
        file,
        base_uri,
        select_default=False,
        form_parser_class=FormParser,
        request_class=_request.Request,
        entitydefs=None,
        encoding=DEFAULT_ENCODING,

        # private
        _urljoin=urlparse.urljoin,
        _urlparse=urlparse.urlparse,
        _urlunparse=urlparse.urlunparse, ):
    """Identical to ParseFile, except that:

    1. The returned list contains an extra item.  The first form in the list
    contains all controls not contained in any FORM element.

    2. The arguments ignore_errors and backwards_compat have been removed.

    3. Backwards-compatibility mode (backwards_compat=True) is not available.
    """
    return _ParseFileEx(
        file,
        base_uri,
        select_default,
        False,
        form_parser_class,
        request_class,
        entitydefs,
        False,
        encoding,
        _urljoin=_urljoin,
        _urlparse=_urlparse,
        _urlunparse=_urlunparse, )


def ParseString(text, base_uri, *args, **kwds):
    fh = StringIO(text)
    return ParseFileEx(fh, base_uri, *args, **kwds)


def ParseResponse(response, *args, **kwds):
    """Parse HTTP response and return a list of HTMLForm instances.

    The return value of mechanize.urlopen can be conveniently passed to this
    function as the response parameter.

    mechanize.ParseError is raised on parse errors.

    response: file-like object (supporting read() method) with a method
     geturl(), returning the URI of the HTTP response
    select_default: for multiple-selection SELECT controls and RADIO controls,
     pick the first item as the default if none are selected in the HTML
    form_parser_class: class to instantiate and use to pass
    request_class: class to return from .click() method (default is
     mechanize.Request)
    entitydefs: mapping like {"&amp;": "&", ...} containing HTML entity
     definitions (a sensible default is used)
    encoding: character encoding used for encoding numeric character references
     when matching link text.  mechanize does not attempt to find the encoding
     in a META HTTP-EQUIV attribute in the document itself (mechanize, for
     example, does do that and will pass the correct value to mechanize using
     this parameter).

    backwards_compat: boolean that determines whether the returned HTMLForm
     objects are backwards-compatible with old code.  If backwards_compat is
     true:

     - ClientForm 0.1 code will continue to work as before.

     - Label searches that do not specify a nr (number or count) will always
       get the first match, even if other controls match.  If
       backwards_compat is False, label searches that have ambiguous results
       will raise an AmbiguityError.

     - Item label matching is done by strict string comparison rather than
       substring matching.

     - De-selecting individual list items is allowed even if the Item is
       disabled.

    The backwards_compat argument will be removed in a future release.

    Pass a true value for select_default if you want the behaviour specified by
    RFC 1866 (the HTML 2.0 standard), which is to select the first item in a
    RADIO or multiple-selection SELECT control if none were selected in the
    HTML.  Most browsers (including Microsoft Internet Explorer (IE) and
    Netscape Navigator) instead leave all items unselected in these cases.  The
    W3C HTML 4.0 standard leaves this behaviour undefined in the case of
    multiple-selection SELECT controls, but insists that at least one RADIO
    button should be checked at all times, in contradiction to browser
    behaviour.

    There is a choice of parsers.  mechanize.XHTMLCompatibleFormParser (uses
    HTMLParser.HTMLParser) works best for XHTML, mechanize.FormParser (uses
    bundled copy of sgmllib.SGMLParser) (the default) works better for ordinary
    grubby HTML.  Note that HTMLParser is only available in Python 2.2 and
    later.  You can pass your own class in here as a hack to work around bad
    HTML, but at your own risk: there is no well-defined interface.

    """
    return _ParseFileEx(response, response.geturl(), *args, **kwds)[1:]


def ParseFile(file, base_uri, *args, **kwds):
    """Parse HTML and return a list of HTMLForm instances.

    mechanize.ParseError is raised on parse errors.

    file: file-like object (supporting read() method) containing HTML with zero
     or more forms to be parsed
    base_uri: the URI of the document (note that the base URI used to submit
     the form will be that given in the BASE element if present, not that of
     the document)

    For the other arguments and further details, see ParseResponse.__doc__.

    """
    return _ParseFileEx(file, base_uri, *args, **kwds)[1:]


def _ParseFileEx(
        file,
        base_uri,
        select_default=False,
        ignore_errors=False,
        form_parser_class=FormParser,
        request_class=_request.Request,
        entitydefs=None,
        backwards_compat=True,
        encoding=DEFAULT_ENCODING,
        _urljoin=urlparse.urljoin,
        _urlparse=urlparse.urlparse,
        _urlunparse=urlparse.urlunparse, ):
    if backwards_compat:
        deprecation("operating in backwards-compatibility mode", 1)
    fp = form_parser_class(entitydefs, encoding)
    while 1:
        data = file.read(CHUNK)
        try:
            fp.feed(data)
        except ParseError, e:
            e.base_uri = base_uri
            raise
        if len(data) != CHUNK:
            break
    fp.close()
    if fp.base is not None:
        # HTML BASE element takes precedence over document URI
        base_uri = fp.base
    labels = []  # Label(label) for label in fp.labels]
    id_to_labels = {}
    for l in fp.labels:
        label = Label(l)
        labels.append(label)
        for_id = l["for"]
        coll = id_to_labels.get(for_id)
        if coll is None:
            id_to_labels[for_id] = [label]
        else:
            coll.append(label)
    forms = []
    for (name, action, method, enctype), attrs, controls in fp.forms:
        if action is None:
            action = base_uri
        else:
            action = _urljoin(base_uri, action)
        # would be nice to make HTMLForm class (form builder) pluggable
        form = HTMLForm(action, method, enctype, name, attrs, request_class,
                        forms, labels, id_to_labels, backwards_compat)
        form._urlparse = _urlparse
        form._urlunparse = _urlunparse
        for ii in range(len(controls)):
            type, name, attrs = controls[ii]
            # index=ii*10 allows ImageControl to return multiple ordered pairs
            form.new_control(
                type,
                name,
                attrs,
                select_default=select_default,
                index=ii * 10)
        forms.append(form)
    for form in forms:
        form.fixup()
    return forms
