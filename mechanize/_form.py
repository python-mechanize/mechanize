from __future__ import absolute_import

import re
from collections import defaultdict

from ._form_controls import HTMLForm, Label, compress_whitespace
from ._request import Request
from ._rfc3986 import clean_url, urlsplit
from ._rfc3986 import urljoin as rfc3986_urljoin
from .polyglot import urljoin, is_string, as_unicode


class SkipControl(ValueError):
    pass


def normalize_line_endings(text):
    return re.sub(as_unicode(r"(?:(?<!\r)\n)|(?:\r(?!\n))"), u"\r\n", text)


# The text inside these elements is not part of the text of a <label> that
# contains them: it is either the content of an embedded control (options,
# textarea default value, button caption), the text of another (invalidly
# nested) label, fallback content, or not rendered text at all.
_LABEL_TEXT_EXCLUDED_SUBTREES = frozenset((
    'select', 'datalist', 'option', 'optgroup', 'textarea', 'button',
    'label', 'meter', 'progress', 'script', 'style', 'template', 'noscript'))


def label_text(elem):
    # Return the text of a <label> element, including text inside nested
    # inline elements, in document order. Comments are ignored and the text of
    # embedded controls is excluded. Iterative, so that deeply nested
    # documents cannot exhaust the recursion limit.
    ans = []
    if elem.text:
        ans.append(elem.text)
    # Each entry is (iterator over children, tail text to emit when done)
    stack = [(iter(elem), None)]
    while stack:
        children, tail = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            if tail:
                ans.append(tail)
            continue
        if (is_string(child.tag) and
                child.tag.lower() not in _LABEL_TEXT_EXCLUDED_SUBTREES):
            if child.text:
                ans.append(child.text)
            stack.append((iter(child), child.tail))
        elif child.tail:
            ans.append(child.tail)
    return ''.join(ans)


# <base> elements inside these are not part of the HTML document's base URL
_BASE_EXCLUDED_SUBTREES = frozenset(('svg', 'math', 'template'))


def _find_base_href(root):
    # Return the href of the first <base> element in document order that has
    # one, without descending into the excluded subtrees. Iterative, so that
    # deeply nested documents cannot exhaust the recursion limit.
    stack = [iter((root,))]
    while stack:
        elem = next(stack[-1], None)
        if elem is None:
            stack.pop()
            continue
        if not is_string(elem.tag):
            continue
        q = elem.tag.lower()
        if q == 'base':
            href = elem.get('href')
            if href is not None:
                return href
        elif q not in _BASE_EXCLUDED_SUBTREES:
            stack.append(iter(elem))


def _is_opaque(url):
    # True for URLs such as about:blank and data: URLs that have no
    # hierarchical path to resolve relative references against
    scheme, authority, path = urlsplit(url)[:3]
    return scheme is not None and authority is None and not path.startswith('/')


def resolve_base_url(root, document_url):
    '''
    Return the base URL of the document whose root element is root: the href
    of the first <base> element that has an href attribute, resolved against
    document_url. As in browsers, later <base> elements are ignored and the
    base URL applies to the whole document, including content that precedes
    the <base> element. If there is no such <base> element, or the document
    URL cannot be used as a base for relative URLs, document_url is returned.
    '''
    href = None if root is None else _find_base_href(root)
    if href is None:
        return document_url
    href = clean_url(href)
    if document_url is None:
        return href
    if _is_opaque(document_url) and urlsplit(href)[0] is None:
        # A relative URL cannot be resolved against eg about:blank
        return document_url
    return rfc3986_urljoin(document_url, href)


def parse_control(elem, parent_of, label_text_of, default_type='text'):
    attrs = dict(elem.attrib)
    label_elem = parent_of(elem, 'label')
    if label_elem is not None:
        lt = label_text_of(label_elem)
        if lt is not None:
            attrs["__label"] = lt
    ctype = attrs.get('type') or default_type
    return ctype, attrs.get('name'), attrs


def parse_input(elem, parent_of, label_text_of, attrs_map):
    return parse_control(elem, parent_of, label_text_of)


def parse_button(elem, parent_of, label_text_of, attrs_map):
    ctype, name, attrs = parse_control(
        elem, parent_of, label_text_of, default_type='submit')
    ctype += 'button'
    return ctype, name, attrs


def parse_option(elem, parent_of, label_text_of, attrs_map):
    ctype, name, attrs = parse_control(elem, parent_of, label_text_of)
    og = parent_of(elem, 'optgroup')
    contents = (elem.text or '').strip()
    attrs['contents'] = contents
    attrs['value'] = attrs.get('value', contents)
    attrs['label'] = attrs.get('label', contents)
    if og is not None and og.get('disabled') is not None:
        attrs['disabled'] = 'disabled'
    sel = parent_of(elem, 'select')
    if sel is None:
        raise SkipControl()
    attrs['__select'] = sel = attrs_map[sel]['__select']
    return 'select', sel.get('name'), attrs


def parse_textarea(elem, parent_of, label_text_of, attrs_map):
    ctype, name, attrs = parse_control(elem, parent_of, label_text_of)
    ctype = 'textarea'
    attrs['value'] = normalize_line_endings(elem.text or u'')
    return ctype, name, attrs


def parse_select(elem, parent_of, label_text_of, attrs_map):
    ctype, name, attrs = parse_control(elem, parent_of, label_text_of)
    ctype = 'select'
    return ctype, name, {'__select': attrs}


def parse_forms(root, base_url, request_class=None, select_default=False, encoding=None):
    # base_url is the URL of the document, any <base> element is applied below
    document_url = base_url
    if request_class is None:
        request_class = Request
    forms, labels = [], []
    form_elems = []
    form_id_map = {}
    all_elems = tuple(
        e for e in root.iter('*') if is_string(e.tag))
    parent_map = {c: p for p in all_elems for c in p}
    id_to_labels = defaultdict(list)
    base_url = resolve_base_url(root, document_url)
    global_form = HTMLForm(document_url, encoding=encoding, base_url=base_url)
    label_texts = {}

    def label_text_of(label_elem):
        # Cached, as a <label> can wrap many controls and walking its subtree
        # for each of them would be quadratic. Returns None if the label has
        # no text at all, otherwise its whitespace-compressed text.
        try:
            return label_texts[label_elem]
        except KeyError:
            lt = label_text(label_elem)
            ans = label_texts[label_elem] = (
                compress_whitespace(lt) if lt else None)
            return ans

    for e in all_elems:
        q = e.tag.lower()
        if q == 'form':
            form_elems.append(e)
            fid = e.get('id')
            if fid:
                form_id_map[fid] = e
        elif q == 'label':
            for_id = e.get('for')
            if for_id is not None:
                label = Label(label_text_of(e), for_id)
                labels.append(label)
                id_to_labels[for_id].append(label)

    def parent_of(elem, parent_name):
        q = elem
        while True:
            q = parent_map.get(q)
            if q is None:
                return
            if q.tag.lower() == parent_name:
                return q

    forms_map = {}
    for form_elem in form_elems:
        name = form_elem.get('name') or None
        action = form_elem.get('action') or None
        method = form_elem.get('method') or 'GET'
        enctype = form_elem.get(
            'enctype') or "application/x-www-form-urlencoded"
        if action:
            action = urljoin(base_url, action)
        else:
            # A missing or empty action submits to the document URL, not to
            # the base URL
            action = base_url if document_url is None else document_url
        form = HTMLForm(action, method, enctype, name, form_elem.attrib,
                        request_class, forms, labels, id_to_labels,
                        encoding=encoding, base_url=base_url)
        forms_map[form_elem] = form
        forms.append(form)

    attrs_map = {}
    control_names = {
        'option': parse_option,
        'button': parse_button,
        'input': parse_input,
        'textarea': parse_textarea,
        'select': parse_select,
    }

    for i, elem in enumerate(all_elems):
        q = elem.tag.lower()
        cfunc = control_names.get(q)
        if cfunc is not None:
            fid = elem.get('form')
            if fid and fid in form_id_map:
                form_elem = form_id_map[fid]
            else:
                form_elem = parent_of(elem, 'form')
            form = forms_map.get(form_elem, global_form)
            try:
                control_type, control_name, attrs = cfunc(
                    elem, parent_of, label_text_of, attrs_map)
            except SkipControl:
                continue
            attrs_map[elem] = attrs
            form.new_control(
                control_type,
                control_name,
                attrs,
                index=i * 10,
                select_default=select_default)

    for form in forms:
        form.fixup()
    global_form.fixup()

    return forms, global_form
