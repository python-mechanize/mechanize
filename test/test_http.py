#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


from unittest import TestCase

from mechanize._http import MechanizeRobotFileParser


class TestRobotFileParser(TestCase):

    def test_set_opener(self):
        rfp = MechanizeRobotFileParser()
        rfp.set_opener()
        q = '<mechanize._opener.OpenerDirector object at '
        self.assertTrue(repr(rfp._opener).startswith(q))
