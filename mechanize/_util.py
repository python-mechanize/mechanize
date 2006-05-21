"""Python backwards-compat., date/time routines, seekable file object wrapper.

 Copyright 2002-2006 John J Lee <jjl@pobox.com>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

import re, string, time, copy, urllib, mimetools
from types import TupleType
from cStringIO import StringIO

def startswith(string, initial):
    if len(initial) > len(string): return False
    return string[:len(initial)] == initial

def endswith(string, final):
    if len(final) > len(string): return False
    return string[-len(final):] == final

def isstringlike(x):
    try: x+""
    except: return False
    else: return True

SPACE_DICT = {}
for c in string.whitespace:
    SPACE_DICT[c] = None
del c
def isspace(string):
    for c in string:
        if not SPACE_DICT.has_key(c): return False
    return True

## def caller():
##     try:
##         raise SyntaxError
##     except:
##         import sys
##     return sys.exc_traceback.tb_frame.f_back.f_back.f_code.co_name


# this is here rather than in _HeadersUtil as it's just for
# compatibility with old Python versions, rather than entirely new code
def getheaders(msg, name):
    """Get all values for a header.

    This returns a list of values for headers given more than once; each
    value in the result list is stripped in the same way as the result of
    getheader().  If the header is not given, return an empty list.
    """
    result = []
    current = ''
    have_header = 0
    for s in msg.getallmatchingheaders(name):
        if isspace(s[0]):
            if current:
                current = "%s\n %s" % (current, string.strip(s))
            else:
                current = string.strip(s)
        else:
            if have_header:
                result.append(current)
            current = string.strip(s[string.find(s, ":") + 1:])
            have_header = 1
    if have_header:
        result.append(current)
    return result

from calendar import timegm

# Date/time conversion routines for formats used by the HTTP protocol.

EPOCH = 1970
def my_timegm(tt):
    year, month, mday, hour, min, sec = tt[:6]
    if ((year >= EPOCH) and (1 <= month <= 12) and (1 <= mday <= 31) and
        (0 <= hour <= 24) and (0 <= min <= 59) and (0 <= sec <= 61)):
        return timegm(tt)
    else:
        return None

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
months_lower = []
for month in months: months_lower.append(string.lower(month))


def time2isoz(t=None):
    """Return a string representing time in seconds since epoch, t.

    If the function is called without an argument, it will use the current
    time.

    The format of the returned string is like "YYYY-MM-DD hh:mm:ssZ",
    representing Universal Time (UTC, aka GMT).  An example of this format is:

    1994-11-24 08:49:37Z

    """
    if t is None: t = time.time()
    year, mon, mday, hour, min, sec = time.gmtime(t)[:6]
    return "%04d-%02d-%02d %02d:%02d:%02dZ" % (
        year, mon, mday, hour, min, sec)

def time2netscape(t=None):
    """Return a string representing time in seconds since epoch, t.

    If the function is called without an argument, it will use the current
    time.

    The format of the returned string is like this:

    Wed, DD-Mon-YYYY HH:MM:SS GMT

    """
    if t is None: t = time.time()
    year, mon, mday, hour, min, sec, wday = time.gmtime(t)[:7]
    return "%s %02d-%s-%04d %02d:%02d:%02d GMT" % (
        days[wday], mday, months[mon-1], year, hour, min, sec)


UTC_ZONES = {"GMT": None, "UTC": None, "UT": None, "Z": None}

timezone_re = re.compile(r"^([-+])?(\d\d?):?(\d\d)?$")
def offset_from_tz_string(tz):
    offset = None
    if UTC_ZONES.has_key(tz):
        offset = 0
    else:
        m = timezone_re.search(tz)
        if m:
            offset = 3600 * int(m.group(2))
            if m.group(3):
                offset = offset + 60 * int(m.group(3))
            if m.group(1) == '-':
                offset = -offset
    return offset

def _str2time(day, mon, yr, hr, min, sec, tz):
    # translate month name to number
    # month numbers start with 1 (January)
    try:
        mon = months_lower.index(string.lower(mon))+1
    except ValueError:
        # maybe it's already a number
        try:
            imon = int(mon)
        except ValueError:
            return None
        if 1 <= imon <= 12:
            mon = imon
        else:
            return None

    # make sure clock elements are defined
    if hr is None: hr = 0
    if min is None: min = 0
    if sec is None: sec = 0

    yr = int(yr)
    day = int(day)
    hr = int(hr)
    min = int(min)
    sec = int(sec)

    if yr < 1000:
        # find "obvious" year
        cur_yr = time.localtime(time.time())[0]
        m = cur_yr % 100
        tmp = yr
        yr = yr + cur_yr - m
        m = m - tmp
        if abs(m) > 50:
            if m > 0: yr = yr + 100
            else: yr = yr - 100

    # convert UTC time tuple to seconds since epoch (not timezone-adjusted)
    t = my_timegm((yr, mon, day, hr, min, sec, tz))

    if t is not None:
        # adjust time using timezone string, to get absolute time since epoch
        if tz is None:
            tz = "UTC"
        tz = string.upper(tz)
        offset = offset_from_tz_string(tz)
        if offset is None:
            return None
        t = t - offset

    return t


strict_re = re.compile(r"^[SMTWF][a-z][a-z], (\d\d) ([JFMASOND][a-z][a-z]) (\d\d\d\d) (\d\d):(\d\d):(\d\d) GMT$")
wkday_re = re.compile(
    r"^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\s*", re.I)
loose_http_re = re.compile(
    r"""^
    (\d\d?)            # day
       (?:\s+|[-\/])
    (\w+)              # month
        (?:\s+|[-\/])
    (\d+)              # year
    (?:
          (?:\s+|:)    # separator before clock
       (\d\d?):(\d\d)  # hour:min
       (?::(\d\d))?    # optional seconds
    )?                 # optional clock
       \s*
    ([-+]?\d{2,4}|(?![APap][Mm]\b)[A-Za-z]+)? # timezone
       \s*
    (?:\(\w+\))?       # ASCII representation of timezone in parens.
       \s*$""", re.X)
def http2time(text):
    """Returns time in seconds since epoch of time represented by a string.

    Return value is an integer.

    None is returned if the format of str is unrecognized, the time is outside
    the representable range, or the timezone string is not recognized.  If the
    string contains no timezone, UTC is assumed.

    The timezone in the string may be numerical (like "-0800" or "+0100") or a
    string timezone (like "UTC", "GMT", "BST" or "EST").  Currently, only the
    timezone strings equivalent to UTC (zero offset) are known to the function.

    The function loosely parses the following formats:

    Wed, 09 Feb 1994 22:23:32 GMT       -- HTTP format
    Tuesday, 08-Feb-94 14:15:29 GMT     -- old rfc850 HTTP format
    Tuesday, 08-Feb-1994 14:15:29 GMT   -- broken rfc850 HTTP format
    09 Feb 1994 22:23:32 GMT            -- HTTP format (no weekday)
    08-Feb-94 14:15:29 GMT              -- rfc850 format (no weekday)
    08-Feb-1994 14:15:29 GMT            -- broken rfc850 format (no weekday)

    The parser ignores leading and trailing whitespace.  The time may be
    absent.

    If the year is given with only 2 digits, the function will select the
    century that makes the year closest to the current date.

    """
    # fast exit for strictly conforming string
    m = strict_re.search(text)
    if m:
        g = m.groups()
        mon = months_lower.index(string.lower(g[1])) + 1
        tt = (int(g[2]), mon, int(g[0]),
              int(g[3]), int(g[4]), float(g[5]))
        return my_timegm(tt)

    # No, we need some messy parsing...

    # clean up
    text = string.lstrip(text)
    text = wkday_re.sub("", text, 1)  # Useless weekday

    # tz is time zone specifier string
    day, mon, yr, hr, min, sec, tz = [None]*7

    # loose regexp parse
    m = loose_http_re.search(text)
    if m is not None:
        day, mon, yr, hr, min, sec, tz = m.groups()
    else:
        return None  # bad format

    return _str2time(day, mon, yr, hr, min, sec, tz)


iso_re = re.compile(
    """^
    (\d{4})              # year
       [-\/]?
    (\d\d?)              # numerical month
       [-\/]?
    (\d\d?)              # day
   (?:
         (?:\s+|[-:Tt])  # separator before clock
      (\d\d?):?(\d\d)    # hour:min
      (?::?(\d\d(?:\.\d*)?))?  # optional seconds (and fractional)
   )?                    # optional clock
      \s*
   ([-+]?\d\d?:?(:?\d\d)?
    |Z|z)?               # timezone  (Z is "zero meridian", i.e. GMT)
      \s*$""", re.X)
def iso2time(text):
    """
    As for http2time, but parses the ISO 8601 formats:

    1994-02-03 14:15:29 -0100    -- ISO 8601 format
    1994-02-03 14:15:29          -- zone is optional
    1994-02-03                   -- only date
    1994-02-03T14:15:29          -- Use T as separator
    19940203T141529Z             -- ISO 8601 compact format
    19940203                     -- only date

    """
    # clean up
    text = string.lstrip(text)

    # tz is time zone specifier string
    day, mon, yr, hr, min, sec, tz = [None]*7

    # loose regexp parse
    m = iso_re.search(text)
    if m is not None:
        # XXX there's an extra bit of the timezone I'm ignoring here: is
        #   this the right thing to do?
        yr, mon, day, hr, min, sec, tz, _ = m.groups()
    else:
        return None  # bad format

    return _str2time(day, mon, yr, hr, min, sec, tz)


# XXX Andrew Dalke kindly sent me a similar class in response to my request on
# comp.lang.python, which I then proceeded to lose.  I wrote this class
# instead, but I think he's released his code publicly since, could pinch the
# tests from it, at least...

# For testing seek_wrapper invariant (note that
# test_urllib2.HandlerTest.test_seekable is expected to fail when this
# invariant checking is turned on).  The invariant checking is done by module
# ipdc, which is available here:
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/436834
## from ipdbc import ContractBase
## class seek_wrapper(ContractBase):
class seek_wrapper:
    """Adds a seek method to a file object.

    This is only designed for seeking on readonly file-like objects.

    Wrapped file-like object must have a read method.  The readline method is
    only supported if that method is present on the wrapped object.  The
    readlines method is always supported.  xreadlines and iteration are
    supported only for Python 2.2 and above.

    Public attribute: wrapped (the wrapped file object).

    WARNING: All other attributes of the wrapped object (ie. those that are not
    one of wrapped, read, readline, readlines, xreadlines, __iter__ and next)
    are passed through unaltered, which may or may not make sense for your
    particular file object.

    """
    # General strategy is to check that cache is full enough, then delegate to
    # the cache (self.__cache, which is a cStringIO.StringIO instance).  A seek
    # position (self.__pos) is maintained independently of the cache, in order
    # that a single cache may be shared between multiple seek_wrapper objects.
    # Copying using module copy shares the cache in this way.

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.__have_readline = hasattr(self.wrapped, "readline")
        self.__cache = StringIO()
        self.__pos = 0  # seek position

    def invariant(self):
        # The end of the cache is always at the same place as the end of the
        # wrapped file.
        return self.wrapped.tell() == len(self.__cache.getvalue())

    def __getattr__(self, name):
        wrapped = self.__dict__.get("wrapped")
        if wrapped:
            return getattr(wrapped, name)
        return getattr(self.__class__, name)

    def seek(self, offset, whence=0):
        assert whence in [0,1,2]

        # how much data, if any, do we need to read?
        if whence == 2:  # 2: relative to end of *wrapped* file
            if offset < 0: raise ValueError("negative seek offset")
            # since we don't know yet where the end of that file is, we must
            # read everything
            to_read = None
        else:
            if whence == 0:  # 0: absolute
                if offset < 0: raise ValueError("negative seek offset")
                dest = offset
            else:  # 1: relative to current position
                pos = self.__pos
                if pos < offset:
                    raise ValueError("seek to before start of file")
                dest = pos + offset
            end = len(self.__cache.getvalue())
            to_read = dest - end
            if to_read < 0:
                to_read = 0

        if to_read != 0:
            self.__cache.seek(0, 2)
            if to_read is None:
                assert whence == 2
                self.__cache.write(self.wrapped.read())
                self.__pos = self.__cache.tell() - offset
            else:
                self.__cache.write(self.wrapped.read(to_read))
                # Don't raise an exception even if we've seek()ed past the end
                # of .wrapped, since fseek() doesn't complain in that case.
                # Also like fseek(), pretend we have seek()ed past the end,
                # i.e. not:
                #self.__pos = self.__cache.tell()
                # but rather:
                self.__pos = dest
        else:
            self.__pos = dest

    def tell(self):
        return self.__pos

    def __copy__(self):
        cpy = self.__class__(self.wrapped)
        cpy.__cache = self.__cache
        return cpy

    def get_data(self):
        pos = self.__pos
        try:
            self.seek(0)
            return self.read(-1)
        finally:
            self.__pos = pos

    def read(self, size=-1):
        pos = self.__pos
        end = len(self.__cache.getvalue())
        available = end - pos

        # enough data already cached?
        if size <= available and size != -1:
            self.__cache.seek(pos)
            self.__pos = pos+size
            return self.__cache.read(size)

        # no, so read sufficient data from wrapped file and cache it
        self.__cache.seek(0, 2)
        if size == -1:
            self.__cache.write(self.wrapped.read())
        else:
            to_read = size - available
            assert to_read > 0
            self.__cache.write(self.wrapped.read(to_read))
        self.__cache.seek(pos)

        data = self.__cache.read(size)
        self.__pos = self.__cache.tell()
        assert self.__pos == pos + len(data)
        return data

    def readline(self, size=-1):
        if not self.__have_readline:
            raise NotImplementedError("no readline method on wrapped object")

        # line we're about to read might not be complete in the cache, so
        # read another line first
        pos = self.__pos
        self.__cache.seek(0, 2)
        self.__cache.write(self.wrapped.readline())
        self.__cache.seek(pos)

        data = self.__cache.readline()
        if size != -1:
            r = data[:size]
            self.__pos = pos+size
        else:
            r = data
            self.__pos = pos+len(data)
        return r

    def readlines(self, sizehint=-1):
        pos = self.__pos
        self.__cache.seek(0, 2)
        self.__cache.write(self.wrapped.read())
        self.__cache.seek(pos)
        data = self.__cache.readlines(sizehint)
        self.__pos = self.__cache.tell()
        return data

    def __iter__(self): return self
    def next(self):
        line = self.readline()
        if line == "": raise StopIteration
        return line

    xreadlines = __iter__

    def __repr__(self):
        return ("<%s at %s whose wrapped object = %r>" %
                (self.__class__.__name__, hex(id(self)), self.wrapped))


class response_seek_wrapper(seek_wrapper):

    """
    Supports copying response objects and setting response body data.

    """

    def __init__(self, wrapped):
        seek_wrapper.__init__(self, wrapped)
        self._headers = self.wrapped.info()

    def __copy__(self):
        cpy = seek_wrapper.__copy__(self)
        # copy headers from delegate
        cpy._headers = copy.copy(self.info())
        return cpy

    def info(self):
        return self._headers

    def set_data(self, data):
        self.seek(0)
        self.read()
        self.close()
        cache = self._seek_wrapper__cache = StringIO()
        cache.write(data)
        self.seek(0)


class eoffile:
    # file-like object that always claims to be at end-of-file...
    def read(self, size=-1): return ""
    def readline(self, size=-1): return ""
    def __iter__(self): return self
    def next(self): return ""
    def close(self): pass

class eofresponse(eoffile):
    def __init__(self, url, headers, code, msg):
        self._url = url
        self._headers = headers
        self.code = code
        self.msg = msg
    def geturl(self): return self._url
    def info(self): return self._headers


class closeable_response:
    """Avoids unnecessarily clobbering urllib.addinfourl methods on .close().

    Only supports responses returned by mechanize.HTTPHandler.

    After .close(), the following methods are supported:

    .read()
    .readline()
    .readlines()
    .seek()
    .tell()
    .info()
    .geturl()
    .__iter__()
    .next()
    .close()

    and the following attributes are supported:

    .code
    .msg

    Also supports pickling (but the stdlib currently does something to prevent
    it: http://python.org/sf/1144636).

    """
    # presence of this attr indicates is useable after .close()
    closeable_response = None

    def __init__(self, fp, headers, url, code, msg):
        self._set_fp(fp)
        self._headers = headers
        self._url = url
        self.code = code
        self.msg = msg

    def _set_fp(self, fp):
        self.fp = fp
        self.read = self.fp.read
        self.readline = self.fp.readline
        if hasattr(self.fp, "readlines"): self.readlines = self.fp.readlines
        if hasattr(self.fp, "fileno"):
            self.fileno = self.fp.fileno
        else:
            self.fileno = lambda: None
        if hasattr(self.fp, "__iter__"):
            self.__iter__ = self.fp.__iter__
            if hasattr(self.fp, "next"):
                self.next = self.fp.next

    def __repr__(self):
        return '<%s at %s whose fp = %r>' % (
            self.__class__.__name__, hex(id(self)), self.fp)

    def info(self):
        return self._headers

    def geturl(self):
        return self._url

    def close(self):
        wrapped = self.fp
        wrapped.close()
        new_wrapped = eofresponse(
            self._url, self._headers, self.code, self.msg)
        self._set_fp(new_wrapped)

    def __getstate__(self):
        # There are three obvious options here:
        # 1. truncate
        # 2. read to end
        # 3. close socket, pickle state including read position, then open
        #    again on unpickle and use Range header
        # XXXX um, 4. refuse to pickle unless .close()d.  This is better,
        #  actually ("errors should never pass silently").  Pickling doesn't
        #  work anyway ATM, because of http://python.org/sf/1144636 so fix
        #  this later

        # 2 breaks pickle protocol, because one expects the original object
        # to be left unscathed by pickling.  3 is too complicated and
        # surprising (and too much work ;-) to happen in a sane __getstate__.
        # So we do 1.

        state = self.__dict__.copy()
        new_wrapped = eofresponse(
            self._url, self._headers, self.code, self.msg)
        state["wrapped"] = new_wrapped
        return state

def make_response(data, headers, url, code, msg):
    """Convenient factory for objects implementing response interface.

    data: string containing response body data
    headers: sequence of (name, value) pairs
    url: URL of response
    code: integer response code (e.g. 200)
    msg: string response code message (e.g. "OK")

    """
    hdr_text = []
    for name_value in headers:
        hdr_text.append("%s: %s" % name_value)
    mime_headers = mimetools.Message(StringIO("\n".join(hdr_text)))
    r = closeable_response(StringIO(data), mime_headers, url, code, msg)
    return response_seek_wrapper(r)
