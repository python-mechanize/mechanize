"""Generic connection cache manager.

WARNING: THIS MODULE IS UNUSED AND UNTESTED!

Example:

 from mechanize import ConnectionCache
 cache = ConnectionCache()
 cache.deposit("http", "example.com", conn)
 conn = cache.withdraw("http", "example.com")


The ConnectionCache class provides cache expiration.


Copyright (C) 2004-2006 John J Lee <jjl@pobox.com>.
Copyright (C) 2001 Gisle Aas.

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD or ZPL 2.1 licenses (see the file
COPYING.txt included with the distribution).

"""

# Ported from libwww-perl 5.75.

import time
try:
    from types import StringTypes
except ImportError:
    from types import StringType
    StringTypes = StringType

from _Debug import warn
import logging
debug = logging.getLogger("mechanize").debug

warn("WARNING: MODULE _ConnCache IS UNUSED AND UNTESTED!")


class _ConnectionRecord:
    def __init__(self, conn, scheme, key, time):
        self.conn, self.scheme, self.key, self.time = conn, scheme, key, time
    def __repr__(self):
        return "%s(%s, %s, %s, %s)" % (
            self.__class__.__name__,
            self.conn, self.scheme, self.key, self.time)

class ConnectionCache:
    """
    For specialized cache policy it makes sense to subclass ConnectionCache and
    perhaps override the .deposit(), ._enforce_limits() and ._dropping()
    methods.

    """
    def __init__(self, total_capacity=1):
        self._limit = {}
        self.total_capacity(total_capacity)

    def set_total_capacity(self, nr_connections):
        """Set limit for number of cached connections.

        Connections will start to be dropped when this limit is reached.  If 0,
        all connections are immediately dropped.  None means no limit.

        """
        self._limit_total = nr_connections
        self._enforce_limits()

    def total_capacity(self):
        """Return limit for number of cached connections."""
        return self._limit_total

    def set_capacity(self, scheme, nr_connections):
        """Set limit for number of cached connections of specifed scheme.

        scheme: URL scheme (eg. "http" or "ftp")

        """
        self._limit[scheme] = nr_connections
        self._enforce_limits(scheme)

    def capacity(self, scheme):
        """Return limit for number of cached connections of specifed scheme.

        scheme: URL scheme (eg. "http" or "ftp")

        """
        return self._limit[scheme]

    def drop(self, checker=None, reason=None):
        """Drop connections by some criteria.

        checker: either a callable, a number, a string, or None:
         If callable: called for each connection with arguments (conn, scheme,
          key, deposit_time); if it returns a true value, the connection is
          dropped (default is to drop all connections).
         If a number: all connections untouched for the given number of seconds
          or more are dropped.
         If a string: all connections of the given scheme are dropped.
         If None: all connections are dropped.
        reason: passed on to the dropped() method

        """
        if not callable(checker):
            if checker is None:
                checker = lambda cr: True  # drop all of them
            elif isinstance(checker, StringTypes):
                scheme = checker
                if reason is None:
                    reason = "drop %s" % scheme
                checker = lambda cr, scheme=scheme: cr.scheme == scheme
            else:  # numeric
                age_limit = checker
                time_limit = time.time() - age_limit
                if reason is None:
                    reason = "older than %s" % age_limit
                checker = lambda cr, time_limit=time_limit: cr.time < time_limit
        if reason is None:
            reason = "drop"

##         local $SIG{__DIE__};  # don't interfere with eval below
##         local $@;
        crs = []
        for cr in self._conns:
            if checker(cr):
                self._dropping(cr, reason)
                drop = drop + 1
            if not drop:
                crs.append(cr)
        self._conns = crs

    def prune(self):
        """Drop all dead connections.

        This is tested by calling the .ping() method on the connections.  If
        the .ping() method exists and returns a false value, then the
        connection is dropped.

        """
        # XXX HTTPConnection doesn't have a .ping() method
        #self.drop(lambda cr: not cr.conn.ping(), "ping")
        pass

    def get_schemes(self):
        """Return list of cached connection URL schemes."""
        t = {}
        for cr in self._conns:
            t[cr.scheme] = None
        return t.keys()

    def get_connections(self, scheme=None):
        """Return list of all connection objects with the specified URL scheme.

        If no scheme is specified then all connections are returned.

        """
        cs = []
        for cr in self._conns:
            if scheme is None or (scheme and scheme == cr.scheme):
                c.append(cr.conn)
        return cs

# -------------------------------------------------------------------------
# Methods called by handlers to try to save away connections and get them
# back again.

    def deposit(self, scheme, key, conn):
        """Add a new connection to the cache.

        scheme: URL scheme (eg. "http")
        key: any object that can act as a dict key (usually a string or a
         tuple)

        As a side effect, other already cached connections may be dropped.
        Multiple connections with the same scheme/key might be added.

        """
        self._conns.append(_ConnectionRecord(conn, scheme, key, time.time()))
        self._enforce_limits(scheme)

    def withdraw(self, scheme, key):
        """Try to fetch back a connection that was previously deposited.

        If no cached connection with the specified scheme/key is found, then
        None is returned.  There is no guarantee that a deposited connection
        can be withdrawn, as the cache manger is free to drop connections at
        any time.

        """
        conns = self._conns
        for i in range(len(conns)):
            cr = conns[i]
            if not (cr.scheme == scheme and cr.key == key):
                continue
            conns.pop(i)  # remove it
            return cr.conn
        return None

# -------------------------------------------------------------------------
# Called internally.  Subclasses might want to override these.

    def _enforce_limits(self, scheme=None):
        """Drop some cached connections, if necessary.

        Called after a new connection is added (deposited) in the cache or
        capacity limits are adjusted.

        The default implementation drops connections until the specified
        capacity limits are not exceeded.

        """
        conns = self._conns
        if scheme:
            schemes = [scheme]
        else:
            schemes = self.get_schemes()
        for scheme in schemes:
            limit = self._limit.get(scheme)
            if limit is None:
                continue
            for i in range(len(conns), 0, -1):
                if conns[i].scheme != scheme:
                    continue
                limit = limit - 1
                if limit < 0:
                    self._dropping(
                        conns.pop(i),
                        "connection cache %s capacity exceeded" % scheme)

        total = self._limit_total
        if total is not None:
            while len(conns) > total:
                self._dropping(conns.pop(0),
                               "connection cache total capacity exceeded")

    def _dropping(self, conn_record, reason):
        """Called when a connection is dropped.

        conn_record: _ConnectionRecord instance for the dropped connection
        reason: string describing the reason for the drop

        """
        debug("DROPPING %s [%s]" % (conn_record, reason))
