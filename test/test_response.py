"""Tests for mechanize._response.seek_wrapper and friends."""

import copy
from io import BytesIO
from unittest import TestCase

import mechanize


class TestUnSeekable:
    def __init__(self, text):
        if not isinstance(text, bytes):
            text = text.encode('utf-8')
        self._file = BytesIO(text)
        self.log = []

    def tell(self):
        return self._file.tell()

    def seek(self, offset, whence=0):
        assert False

    def read(self, size=-1):
        self.log.append(("read", size))
        return self._file.read(size)

    def readline(self, size=-1):
        self.log.append(("readline", size))
        return self._file.readline(size)

    def readlines(self, sizehint=-1):
        self.log.append(("readlines", sizehint))
        return self._file.readlines(sizehint)


class TestUnSeekableResponse(TestUnSeekable):
    def __init__(self, text, headers):
        TestUnSeekable.__init__(self, text)
        self.code = 200
        self.msg = "OK"
        self.headers = headers
        self.url = "http://example.com/"

    def geturl(self):
        return self.url

    def info(self):
        return self.headers

    def close(self):
        pass


class SeekableTests(TestCase):

    text = b"""\
The quick brown fox
jumps over the lazy

dog.

"""
    text_lines = list(map(lambda l: l + b"\n", text.split(b"\n")[:-1]))

    def testSeekable(self):
        from mechanize._response import seek_wrapper
        text = self.text
        for ii in range(1, 6):
            fh = TestUnSeekable(text)
            sfh = seek_wrapper(fh)
            test = getattr(self, "_test%d" % ii)
            test(sfh)

        # copies have independent seek positions
        fh = TestUnSeekable(text)
        sfh = seek_wrapper(fh)
        self._testCopy(sfh)

    def _testCopy(self, sfh):
        sfh2 = copy.copy(sfh)
        sfh.read(10)
        text = self.text
        self.assertEqual(sfh2.read(10), text[:10])
        sfh2.seek(5)
        self.assertEqual(sfh.read(10), text[10:20])
        self.assertEqual(sfh2.read(10), text[5:15])
        sfh.seek(0)
        sfh2.seek(0)
        return sfh2

    def _test1(self, sfh):
        text = self.text
        text_lines = self.text_lines
        assert sfh.read(10) == text[:10]  # calls fh.read
        assert sfh.log[-1] == ("read", 10)  # .log delegated to fh
        sfh.seek(0)  # doesn't call fh.seek
        assert sfh.read(10) == text[:10]  # doesn't call fh.read
        assert len(sfh.log) == 1
        sfh.seek(0)
        assert sfh.read(5) == text[:5]  # read only part of cached data
        assert len(sfh.log) == 1
        sfh.seek(0)
        assert sfh.read(25) == text[:25]  # calls fh.read
        assert sfh.log[1] == ("read", 15)
        lines = []
        sfh.seek(-1, 1)
        while 1:
            ln = sfh.readline()
            if not ln:
                break
            lines.append(ln)
        assert lines == [b"s over the lazy\n"] + text_lines[2:]
        assert sfh.log[2:] == [("readline", -1)] * 5
        sfh.seek(0)
        lines = []
        while 1:
            ln = sfh.readline()
            if not ln:
                break
            lines.append(ln)
        assert lines == text_lines

    def _test2(self, sfh):
        text = self.text
        sfh.read(5)
        sfh.seek(0)
        assert sfh.read() == text
        assert not sfh.read()
        sfh.seek(0)
        assert sfh.read() == text
        sfh.seek(0)
        assert sfh.readline(5) == b"The q"
        assert sfh.read() == text[5:]
        sfh.seek(0)
        assert sfh.readline(5) == b"The q"
        assert sfh.readline() == b"uick brown fox\n"

    def _test3(self, sfh):
        text_lines = self.text_lines
        sfh.read(25)
        sfh.seek(-1, 1)
        self.assertEqual(sfh.readlines(),
                         [b"s over the lazy\n"] + text_lines[2:])
        sfh.seek(0)
        assert sfh.readlines() == text_lines

    def _test4(self, sfh):
        text_lines = self.text_lines
        count = 0
        limit = 10
        while count < limit:
            if count == 5:
                self.assertIsNone(next(sfh, None))
                break
            else:
                self.assertEqual(next(sfh), text_lines[count])
            count += 1
        else:
            assert False, "iterator not exhausted"

    def _test5(self, sfh):
        text = self.text
        sfh.read(10)
        sfh.seek(5)
        self.assertTrue(sfh.invariant())
        sfh.seek(0, 2)
        self.assertTrue(sfh.invariant())
        sfh.seek(0)
        self.assertEqual(sfh.read(), text)

    def testResponseSeekWrapper(self):
        from mechanize import response_seek_wrapper
        hdrs = {"Content-type": "text/html"}
        r = TestUnSeekableResponse(self.text, hdrs)
        rsw = response_seek_wrapper(r)
        rsw2 = self._testCopy(rsw)
        self.assertTrue(rsw is not rsw2)
        self.assertEqual(rsw.info(), rsw2.info())
        self.assertTrue(rsw.info() is not rsw2.info())

        # should be able to close already-closed object
        rsw2.close()
        rsw2.close()

    def testSetResponseData(self):
        from mechanize import response_seek_wrapper
        r = TestUnSeekableResponse(self.text, {'blah': 'yawn'})
        rsw = response_seek_wrapper(r)
        rsw.set_data(b"""\
A Seeming somwhat more than View;
  That doth instruct the Mind
  In Things that ly behind,
""")
        self.assertEqual(rsw.read(9), b"A Seeming")
        self.assertEqual(rsw.read(13), b" somwhat more")
        rsw.seek(0)
        self.assertEqual(rsw.read(9), b"A Seeming")
        self.assertEqual(rsw.readline(), b" somwhat more than View;\n")
        rsw.seek(0)
        self.assertEqual(rsw.readline(),
                         b"A Seeming somwhat more than View;\n")
        rsw.seek(-1, 1)
        self.assertEqual(rsw.read(7), b"\n  That")

        r = TestUnSeekableResponse(self.text, {'blah': 'yawn'})
        rsw = response_seek_wrapper(r)
        rsw.set_data(self.text)
        self._test2(rsw)
        rsw.seek(0)
        self._test4(rsw)

    def testGetResponseData(self):
        from mechanize import response_seek_wrapper
        r = TestUnSeekableResponse(self.text, {'blah': 'yawn'})
        rsw = response_seek_wrapper(r)

        self.assertEqual(rsw.get_data(), self.text)
        self._test2(rsw)
        rsw.seek(0)
        self._test4(rsw)


class DocTests(TestCase):
    def test_read_complete(self):
        text = b"To err is human, to moo, bovine.\n" * 10

        def get_wrapper():
            from mechanize._response import seek_wrapper
            f = BytesIO(text)
            wr = seek_wrapper(f)
            return wr

        wr = get_wrapper()
        self.assertFalse(wr.read_complete)
        wr.read()
        self.assertTrue(wr.read_complete)
        wr.seek(0)
        self.assertTrue(wr.read_complete)

        wr = get_wrapper()
        wr.read(10)
        self.assertFalse(wr.read_complete)
        wr.readline()
        self.assertFalse(wr.read_complete)
        wr.seek(0, 2)
        self.assertTrue(wr.read_complete)
        wr.seek(0)
        self.assertTrue(wr.read_complete)

        wr = get_wrapper()
        wr.readlines()
        self.assertTrue(wr.read_complete)
        wr.seek(0)
        self.assertTrue(wr.read_complete)

        wr = get_wrapper()
        wr.seek(10)
        self.assertFalse(wr.read_complete)
        wr.seek(1000000)

        wr = get_wrapper()
        wr.read(1000000)
        # we read to the end, but don't know it yet
        self.assertFalse(wr.read_complete)
        wr.read(10)
        self.assertTrue(wr.read_complete)

        wr = get_wrapper()
        wr.read(len(text) - 10)
        self.assertFalse(wr.read_complete)
        wr.readline()
        # we read to the end, but don't know it yet
        self.assertFalse(wr.read_complete)
        wr.readline()
        self.assertTrue(wr.read_complete)

        # Test copying and sharing of .read_complete state

        wr = get_wrapper()
        wr2 = copy.copy(wr)
        self.assertFalse(wr.read_complete)
        self.assertFalse(wr2.read_complete)
        wr2.read()
        self.assertTrue(wr.read_complete)
        self.assertTrue(wr2.read_complete)

        # Fix from -r36082: .read() after .close() used to break
        # .read_complete state

        from mechanize._response import test_response
        r = test_response(text)
        r.read(64)
        r.close()
        self.assertFalse(r.read_complete)
        self.assertFalse(r.read())
        ''
        self.assertFalse(r.read_complete)

    def test_upgrade_response(self):
        def is_response(r):
            names = "get_data read readline readlines close seek code msg".split(
            )
            for name in names:
                self.assertTrue(
                    hasattr(r, name), 'No attr named: {}'.format(name))
            self.assertEqual(r.get_data(), b"test data")

        from mechanize._response import upgrade_response, make_headers, make_response, closeable_response, seek_wrapper
        data = b"test data"
        url = "http://example.com/"
        code = 200
        msg = "OK"

        # Normal response (closeable_response wrapped with seek_wrapper): return a copy

        r1 = make_response(data, [], url, code, msg)
        r2 = upgrade_response(r1)
        is_response(r2)
        self.assertIsNot(r1, r2)
        self.assertIs(r1.wrapped, r2.wrapped)

        # closeable_response with no seek_wrapper: wrap with seek_wrapper

        r1 = closeable_response(
            BytesIO(data), make_headers([]), url, code, msg)
        self.assertRaises(AssertionError, is_response, r1)
        r2 = upgrade_response(r1)
        is_response(r2)
        self.assertIsNot(r1, r2)
        self.assertIs(r1, r2.wrapped)

        # addinfourl: extract .fp and wrap it with closeable_response and seek_wrapper

        from mechanize.polyglot import addinfourl
        r1 = addinfourl(BytesIO(data), make_headers([]), url)
        self.assertRaises(AssertionError, is_response, r1)
        r2 = upgrade_response(r1)
        is_response(r2)
        self.assertIsNot(r1, r2)
        self.assertIsNot(r1, r2.wrapped)
        self.assertIs(r1.fp, r2.wrapped.fp)

        # addinfourl with code, msg

        r1 = addinfourl(BytesIO(data), make_headers([]), url)
        r1.code = 206
        r1.msg = "cool"
        r2 = upgrade_response(r1)
        is_response(r2)
        self.assertEqual(r2.code, r1.code)
        self.assertEqual(r2.msg, r1.msg)

        # addinfourl with seek wrapper: cached data is not lost

        r1 = addinfourl(BytesIO(data), make_headers([]), url)
        r1 = seek_wrapper(r1)
        self.assertEqual(r1.read(4), b'test')
        r2 = upgrade_response(r1)
        is_response(r2)

        # addinfourl wrapped with HTTPError -- remains an HTTPError of the same subclass (through horrible trickery)

        hdrs = make_headers([])
        r1 = addinfourl(BytesIO(data), hdrs, url)

        class MyHTTPError(mechanize.HTTPError):
            pass

        r1 = MyHTTPError(url, code, msg, hdrs, r1)
        self.assertRaises(AssertionError, is_response, r1)
        r2 = upgrade_response(r1)
        is_response(r2)
        self.assertIsInstance(r2, MyHTTPError)
        name = MyHTTPError.__module__ + '.' + MyHTTPError.__name__
        self.assertTrue(
            repr(r2).startswith(
                '<httperror_seek_wrapper ({} instance) at'.format(name)))

        # The trickery does not cause double-wrapping

        r3 = upgrade_response(r2)
        is_response(r3)
        self.assertIsNot(r3, r2)
        self.assertIs(r3.wrapped, r2.wrapped)

        # Test dynamically-created class __repr__ for case where we have the module name

        r4 = addinfourl(BytesIO(data), hdrs, url)
        r4 = mechanize.HTTPError(url, code, msg, hdrs, r4)
        r4 = upgrade_response(r4)
        q = '<httperror_seek_wrapper (urllib2.HTTPError instance) at'
        if not mechanize.polyglot.is_py2:
            q = q.replace('urllib2', 'urllib.error')
        self.assertTrue(repr(r4).startswith(q))


if __name__ == "__main__":
    import unittest
    unittest.main()
