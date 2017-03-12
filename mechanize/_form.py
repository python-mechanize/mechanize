from collections import defaultdict
from urlparse import urljoin

from _form_controls import HTMLForm, Label


def parse_control(elem, parent_of):
    attrs = elem.attrib.copy()
    label_elem = parent_of(elem, 'label')
    label_text = None
    if label_elem is not None:
        label_text = label_elem.text
        if label_text:
            attrs["__label"] = label_text
    default_type = 'text' if elem.tag.lower() == 'input' else 'submit'
    ctype = attrs.get('type') or default_type
    return ctype, attrs.get('name'), attrs


def parse_option(elem, parent_of):
    ctype, name, attrs = parse_control(elem, parent_of)
    og = parent_of(elem, 'optgroup')
    if og is not None and og.get('disabled') is not None:
        attrs['disabled'] = 'disabled'
    return ctype, name, attrs


def parse_textarea(elem, parent_of):
    ctype, name, attrs = parse_control(elem, parent_of)
    ctype = 'textarea'
    attrs['value'] = elem.text or u''
    return ctype, name, attrs


def parse_select(elem, parent_of):
    ctype, name, attrs = parse_control(elem, parent_of)
    ctype = 'select'
    attrs['__select'] = attrs
    return ctype, name, attrs


def parse_forms(root, base_url, request_class=None, select_default=False):
    if request_class is None:
        from mechanize import Request
        request_class = Request
    global_form = HTMLForm(base_url)
    forms, labels = [], []
    form_elems = []
    all_elems = tuple(root.iter('*'))
    parent_map = {c: p for p in all_elems for c in p}
    id_to_labels = defaultdict(list)
    for e in all_elems:
        q = e.tag.lower()
        if q == 'form':
            form_elems.append(e)
        elif q == 'label':
            for_id = e.get('for')
            if for_id is not None:
                l = Label(e.text, for_id)
                labels.append(l)
                id_to_labels[for_id].append(l)

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
            action = base_url
        form = HTMLForm(action, method, enctype, name, form_elem.attrib,
                        request_class, forms, labels, id_to_labels)
        forms_map[form_elem] = form
        forms.append(form)

    control_names = {
        'option': parse_option,
        'button': parse_control,
        'input': parse_control,
        'textarea': parse_textarea,
        'select': parse_select,
    }

    for i, elem in enumerate(all_elems):
        q = elem.tag.lower()
        cfunc = control_names.get(q)
        if cfunc is not None:
            form_elem = parent_of(elem, 'form')
            form = forms_map.get(form_elem, global_form)
            control_type, control_name, attrs = cfunc(elem, parent_of)
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
