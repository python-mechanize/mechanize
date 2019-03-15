#!/usr/bin/env python
"""
System Integration Tests for mechanize.Browser.
"""
from __future__ import (
    print_function, unicode_literals, division, absolute_import,
)

# System Imports
import unittest
try:
    import http.server as simplehttpserver
    import http.server as basehttpserver
except ImportError:
    import SimpleHTTPServer as simplehttpserver
    import BaseHTTPServer as basehttpserver
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver
try:
    import urllib.request as urllib_request
except ImportError:
    import urllib2 as urllib_request
import contextlib
import threading
import io
import sys
# Local Imports
import mechanize

class AuthHandler(simplehttpserver.SimpleHTTPRequestHandler):
    """
    Main class to present webpages and authentication.
    """
    def six_getheader(self, key):
        """
        py2/3 compat getheaders
        """
        if sys.version_info.major < 3:
            return self.headers.getheader(key)
        return self.headers.get(key)
    def do_AUTHHEAD(self):
        """
        Send authorization required response
        """
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Auth\"')
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', '/login')
        self.end_headers()

    def do_GET(self):
        """
        Present frontpage with user authentication.
        """
        if not self.six_getheader('Authorization'):
            self.do_AUTHHEAD()
            self.wfile.write(b'No auth header received')
        else:
            if self.six_getheader('Authorization').startswith('Basic '):
                simplehttpserver.SimpleHTTPRequestHandler.do_GET(self)
                return
            self.do_AUTHHEAD()
            self.wfile.write(self.six_getheader('Authorization').encode(
                'ascii', 'replace'
            ))
            self.wfile.write(b'Not authenticated')

class ThreadingSimpleServer(
            socketserver.ThreadingMixIn, basehttpserver.HTTPServer
        ):
    """
    Threaded Test HTTP Server
    """
    @contextlib.contextmanager
    def obtain(self):
        """
        Setup and Teardown thread handler in context manager
        """
        thread = threading.Thread(name='systemtest', target=self.serve_forever)
        thread.start()
        yield None
        self.shutdown()
        thread.join()

class SystemIntegrationTests(unittest.TestCase):
    """
    Basic integration testing with local browser
    """
    def test_auth(self):
        """
        Test Authentication Headers
        """
        # Setup
        port = 8001
        handler = ThreadingSimpleServer(('localhost', port), AuthHandler)
        with handler.obtain():
            url = "http://localhost:%s/" % (port,)
            username = 'fakemcfakeface'
            password = 'pwdmcpwdface'
            b = mechanize.Browser()
            passman = mechanize.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, url, username, password)

            # other authentication handlers
            auth_digest = urllib_request.HTTPDigestAuthHandler(passman)
            auth_basic = urllib_request.HTTPBasicAuthHandler(passman)

            b.set_handle_robots(False) # pylint: disable=no-member
            b.add_handler(auth_digest) # pylint: disable=no-member
            b.add_handler(auth_basic) # pylint: disable=no-member
            req = mechanize.Request(url)
            # Exercise
            b.open(req)
            # Verify
            assert b.response().code == 200

if __name__ == "__main__":
    unittest.main()
