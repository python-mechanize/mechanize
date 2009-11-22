import unittest
from unittest import TestCase

import mechanize


def first_form(text, base_uri="http://example.com/"):
    return mechanize.ParseString(text, base_uri)[0]


class MutationTests(TestCase):

    def test_add_textfield(self):
        form = first_form('<input type="text" name="foo" value="bar" />')
        more = first_form('<input type="text" name="spam" value="eggs" />')
        combined = form.controls + more.controls
        for control in more.controls:
            control.add_to_form(form)
        self.assertEquals(form.controls, combined)


if __name__ == "__main__":
    unittest.main()
