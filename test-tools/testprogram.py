"""Test runner.

Local test HTTP server support and a few other bits and pieces.
"""

# TODO: resurrect cgitb support

import contextlib
import doctest
import errno
import os
import optparse
import socket
import subprocess
import sys
import time
import unittest
import urllib

import mechanize
import mechanize._rfc3986
import mechanize._testcase as _testcase


class ServerStartupError(Exception):

    pass


class ServerProcess:

    def __init__(self, filename, name=None):
        if filename is None:
            raise ValueError('filename arg must be a string')
        if name is None:
            name = filename
        self.name = os.path.basename(name)
        self.port = None
        self.report_hook = lambda msg: None
        self._filename = filename
        self._args = None
        self._process = None

    def _get_args(self):
        """Return list of command line arguments.

        Override me.
        """
        return []

    def start(self):
        self._args = [sys.executable, self._filename]+self._get_args()
        self.report_hook("starting (%s)" % (self._args,))
        self._process = subprocess.Popen(self._args)
        self.report_hook("waiting for startup")
        self._wait_for_startup()
        self.report_hook("running")

    def _wait_for_startup(self):
        def connect():
            self._process.poll()
            if self._process.returncode is not None:
                message = ("server exited on startup with status %d: %r" %
                           (self._process.returncode, self._args))
                raise ServerStartupError(message)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            try:
                sock.connect(('127.0.0.1', self.port))
            finally:
                sock.close()
        backoff(connect, (socket.error,))

    def stop(self):
        """Kill process (forcefully if necessary)."""
        pid = self._process.pid
        if os.name == 'nt':
            kill_windows(pid, self.report_hook)
        else:
            kill_posix(pid, self.report_hook)


def backoff(func, errors,
            initial_timeout=1., hard_timeout=60., factor=1.2):
    starttime = time.time()
    timeout = initial_timeout
    while time.time() < starttime + hard_timeout - 0.01:
        try:
            func()
        except errors, exc:
            time.sleep(timeout)
            timeout *= factor
            hard_limit = hard_timeout - (time.time() - starttime)
            timeout = min(timeout, hard_limit)
        else:
            break
    else:
        raise


def kill_windows(handle, report_hook):
    try:
        import win32api
    except ImportError:
        import ctypes
        ctypes.windll.kernel32.TerminateProcess(int(handle), -1)
    else:
        win32api.TerminateProcess(int(handle), -1)


def kill_posix(pid, report_hook):
    import signal
    os.kill(pid, signal.SIGTERM)

    timeout = 10.
    starttime = time.time()
    report_hook("waiting for exit")
    def do_nothing(*args):
        pass
    old_handler = signal.signal(signal.SIGCHLD, do_nothing)
    try:
        while time.time() < starttime + timeout - 0.01:
            pid, sts = os.waitpid(pid, os.WNOHANG)
            if pid != 0:
                # exited, or error
                break
            newtimeout = timeout - (time.time() - starttime) - 1.
            time.sleep(newtimeout)  # wait for signal
        else:
            report_hook("forcefully killing")
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError, exc:
                if exc.errno != errno.ECHILD:
                    raise
    finally:
        signal.signal(signal.SIGCHLD, old_handler)


class TwistedServerProcess(ServerProcess):

    def __init__(self, uri, name):
        this_dir = os.path.dirname(__file__)
        path = os.path.join(this_dir, "twisted-localserver.py")
        ServerProcess.__init__(self, path, name)
        self.uri = uri
        authority = mechanize._rfc3986.urlsplit(uri)[1]
        host, port = urllib.splitport(authority)
        if port is None:
            port = "80"
        self.port = int(port)
        # def report(msg):
        #     print "%s: %s" % (name, msg)
        report = lambda msg: None
        self.report_hook = report

    def _get_args(self):
        return [str(self.port)]


class ServerCM(object):

    def __init__(self, make_server):
        self._server = None
        self._make_server = make_server

    def __enter__(self):
        assert self._server is None
        server = self._make_server()
        server.start()
        self._server = server
        return self._server

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._server.stop()
        self._server = None


class NullServer(object):

    def __init__(self, uri, name=None):
        self.uri = uri


@contextlib.contextmanager
def trivial_cm(obj):
    yield obj


def add_attributes_to_test_cases(suite, attributes):
    for test in suite:
        if isinstance(test, unittest.TestCase):
            for name, value in attributes.iteritems():
                setattr(test, name, value)
        else:
            try:
                add_attributes_to_test_cases(test, attributes)
            except AttributeError:
                pass


class FixtureCacheSuite(unittest.TestSuite):

    def __init__(self, fixture_factory, *args, **kwds):
        unittest.TestSuite.__init__(self, *args, **kwds)
        self._fixture_factory = fixture_factory

    def run(self, result):
        try:
            super(FixtureCacheSuite, self).run(result)
        finally:
            self._fixture_factory.tear_down()


def toplevel_test(suite, test_attributes):
    suite = FixtureCacheSuite(test_attributes["fixture_factory"], suite)
    add_attributes_to_test_cases(suite, test_attributes)
    return suite


class TestProgram(unittest.TestProgram):

    def __init__(self, default_discovery_args=None,
                 *args, **kwds):
        self._default_discovery_args = default_discovery_args
        unittest.TestProgram.__init__(self, *args, **kwds)

    def _parse_options(self, argv):
        parser = optparse.OptionParser()
        # plain old unittest
        parser.add_option("-v", "--verbose", action="store_true",
                          help="Verbose output")
        parser.add_option("-q", "--quiet", action="store_true",
                          help="No output")
        # test discovery
        parser.add_option("-s", "--start-directory", dest="start", default=".",
                          help='Directory to start discovery ("." default)')
        parser.add_option("-p", "--pattern", dest="pattern",
                          default="test*.py",
                          help='Pattern to match tests ("test*.py" default)')
        parser.add_option("-t", "--top-level-directory", dest="top",
                          default=None,
                          help=("Top level directory of project (defaults to "
                                "start directory)"))
        # mechanize
        parser.add_option("--uri")
        parser.add_option("--no-local-server", action="store_false",
                          dest="run_local_server", default=True,
                          help=("Don't run local test server.  By default, "
                                "this runs the functional tests against "
                                "mechanize sourceforge site, use --uri to "
                                "override that."))
        parser.add_option("--no-proxies", action="store_true")
        parser.add_option("--log",
                          help=('Turn on logging for logger "mechanize" at '
                                'level logging.DEBUG'))

        options, remaining_args = parser.parse_args(argv)
        if len(remaining_args) > 3:
            self.usageExit()

        options.do_discovery = ((len(remaining_args) == 0 and
                                 self._default_discovery_args is not None) or
                                (len(remaining_args) >= 1 and
                                 remaining_args[0].lower() == "discover"))
        if options.do_discovery:
            if len(remaining_args) == 0:
                discovery_args = self._default_discovery_args
            else:
                discovery_args = remaining_args[1:]
            for name, value in zip(("start", "pattern", "top"),
                                   discovery_args):
                setattr(options, name, value)
        else:
            options.test_names = remaining_args
        if options.uri is None:
            if options.run_local_server:
                options.uri = "http://127.0.0.1:8000"
            else:
                options.uri = "http://wwwsearch.sourceforge.net/"
        return options

    def _do_discovery(self, options):
        start_dir = options.start
        pattern = options.pattern
        top_level_dir = options.top
        loader = unittest.TestLoader()
        self.test = loader.discover(start_dir, pattern, top_level_dir)

    def _vanilla_unittest_main(self, options):
        if len(options.test_names) == 0 and self.defaultTest is None:
            # createTests will load tests from self.module
            self.testNames = None
        elif len(options.test_names) > 0:
            self.testNames = options.test_names
        else:
            self.testNames = (self.defaultTest,)
        self.createTests()

    def parseArgs(self, argv):
        options = self._parse_options(argv[1:])
        if options.verbose:
            self.verbosity = 2
        if options.quiet:
            self.verbosity = 0
        if options.do_discovery:
            self._do_discovery(options)
        else:
            self._vanilla_unittest_main(options)

        if options.log:
            level = logging.DEBUG
            # level = logging.INFO
            # level = logging.WARNING
            # level = logging.NOTSET
            logger = logging.getLogger("mechanize")
            logger.setLevel(level)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            logger.addHandler(handler)

        fixture_factory = _testcase.FixtureFactory()
        if options.run_local_server:
            cm = ServerCM(lambda: TwistedServerProcess(
                    options.uri, "local twisted server"))
        else:
            cm = trivial_cm(lambda: NullServer(options.uri))
        fixture_factory.register_context_manager("server", cm)
        test_attributes = dict(uri=options.uri, no_proxies=options.no_proxies,
                               fixture_factory=fixture_factory)
        self.test = toplevel_test(self.test, test_attributes)


main = TestProgram
