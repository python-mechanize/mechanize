"""Local server and cgitb support."""

import cgitb
#cgitb.enable(format="text")

import sys, os, traceback, logging, glob, time
from unittest import defaultTestLoader, TextTestRunner, TestSuite, TestCase, \
     _TextTestResult


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

    def _get_args(self):
        """Return list of command line arguments.

        Override me.
        """
        return []

    def start(self):
        self.report_hook("starting (%s)" % (
            [sys.executable, self._filename]+self._get_args()))
        self._pid = os.spawnv(
            os.P_NOWAIT,
            sys.executable,
            [sys.executable, self._filename]+self._get_args())
        self.report_hook("waiting for startup")
        self._wait_for_startup()
        self.report_hook("running")

    def _wait_for_startup(self):
        import socket
        def connect():
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
        if os.name == 'nt':
            kill_windows(self._pid, self.report_hook)
        else:
            kill_posix(self._pid, self.report_hook)

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

    def __init__(self, name=None):
        top_level_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        path = os.path.join(top_level_dir, "test-tools/twisted-localserver.py")
        ServerProcess.__init__(self, path, name)

    def _get_args(self):
        return [str(self.port)]


class CgitbTextResult(_TextTestResult):
    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        # Skip test runner traceback levels
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next
        if exctype is test.failureException:
            # Skip assert*() traceback levels
            length = self._count_relevant_tb_levels(tb)
            return cgitb.text((exctype, value, tb))
        return cgitb.text((exctype, value, tb))

class CgitbTextTestRunner(TextTestRunner):
    def _makeResult(self):
        return CgitbTextResult(self.stream, self.descriptions, self.verbosity)

def add_uri_attribute_to_test_cases(suite, uri):
    for test in suite._tests:
        if isinstance(test, TestCase):
            test.uri = uri
        else:
            try:
                add_uri_attribute_to_test_cases(test, uri)
            except AttributeError:
                pass


class TestProgram:
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = """\
Usage: %(progName)s [options] [test] [...]

Note not all the functional tests take note of the --uri argument yet --
some currently always access the internet regardless of the --uri and
--run-local-server options.

Options:
  -l, --run-local-server
                   Run a local Twisted HTTP server for the functional
                   tests.  You need Twisted installed for this to work.
                   The server is run on the port given in the --uri
                   option.  If --run-local-server is given but no --uri is
                   given, http://127.0.0.1:8000 is used as the base URI.
                   Also, if you're on Windows and don't have pywin32 or
                   ctypes installed, this option won't work, and you'll
                   have to start up test-tools/localserver.py manually.
  --uri=URL        Base URI for functional tests
                   (test.py does not access the network, unless you tell
                   it to run module functional_tests;
                   functional_tests.py does access the network)
                   e.g. --uri=http://127.0.0.1:8000/
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output

The following options are only available through test.py (you can still run the
functional tests through test.py, just give 'functional_tests' as the module
name to run):

  -u               Skip plain (non-doctest) unittests
  -d               Skip doctests
  -c               Run coverage (requires coverage.py, seems buggy)
  -t               Display tracebacks using cgitb's text mode

"""
    USAGE_EXAMPLES = """
Examples:
  %(progName)s
                 - run all tests
  %(progName)s test_cookies
                 - run module 'test_cookies'
  %(progName)s test_cookies.CookieTests
                 - run all 'test*' test methods in test_cookies.CookieTests
  %(progName)s test_cookies.CookieTests.test_expires
                 - run test_cookies.CookieTests.test_expires

  %(progName)s functional_tests
                 - run the functional tests
  %(progName)s -l functional_tests
                 - start a local Twisted HTTP server and run the functional
                   tests against that, rather than against SourceForge
                   (quicker!)
"""
    def __init__(self, moduleNames, localServerProcess, defaultTest=None,
                 argv=None, testRunner=None, testLoader=defaultTestLoader,
                 defaultUri="http://wwwsearch.sourceforge.net/",
                 usageExamples=USAGE_EXAMPLES,
                 ):
        self.modules = []
        for moduleName in moduleNames:
            module = __import__(moduleName)
            for part in moduleName.split('.')[1:]:
                module = getattr(module, part)
            self.modules.append(module)
        self.uri = None
        self._defaultUri = defaultUri
        if argv is None:
            argv = sys.argv
        self.verbosity = 1
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.usageExamples = usageExamples
        self.runLocalServer = False
        self.parseArgs(argv)
        if self.runLocalServer:
            import urllib
            from mechanize._rfc3986 import urlsplit
            authority = urlsplit(self.uri)[1]
            host, port = urllib.splitport(authority)
            if port is None:
                port = "80"
            try:
                port = int(port)
            except:
                self.usageExit("port in --uri value must be an integer "
                               "(try --uri=http://127.0.0.1:8000/)")
            self._serverProcess = localServerProcess
            def report(msg):
                print "%s: %s" % (localServerProcess.name, msg)
            localServerProcess.port = port
            localServerProcess.report_hook = report

    def usageExit(self, msg=None):
        if msg: print msg
        print (self.USAGE + self.usageExamples) % self.__dict__
        sys.exit(2)

    def parseArgs(self, argv):
        import getopt
        try:
            options, args = getopt.getopt(
                argv[1:],
                'hHvql',
                ['help','verbose','quiet', 'uri=', 'run-local-server'],
                )
            uri = None
            for opt, value in options:
                if opt in ('-h','-H','--help'):
                    self.usageExit()
                if opt in ('--uri',):
                    uri = value
                if opt in ('-q','--quiet'):
                    self.verbosity = 0
                if opt in ('-v','--verbose'):
                    self.verbosity = 2
                if opt in ('-l', '--run-local-server'):
                    self.runLocalServer = True
            if uri is None:
                if self.runLocalServer:
                    uri = "http://127.0.0.1:8000"
                else:
                    uri = self._defaultUri
            self.uri = uri
            if len(args) == 0 and self.defaultTest is None:
                suite = TestSuite()
                for module in self.modules:
                    test = self.testLoader.loadTestsFromModule(module)
                    suite.addTest(test)
                self.test = suite
                add_uri_attribute_to_test_cases(self.test, self.uri)
                return
            if len(args) > 0:
                self.testNames = args
            else:
                self.testNames = (self.defaultTest,)
            self.createTests()
            add_uri_attribute_to_test_cases(self.test, self.uri)
        except getopt.error, msg:
            self.usageExit(msg)

    def createTests(self):
        self.test = self.testLoader.loadTestsFromNames(self.testNames)

    def runTests(self):
        if self.testRunner is None:
            self.testRunner = TextTestRunner(verbosity=self.verbosity)

        if self.runLocalServer:
            self._serverProcess.start()
        try:
            result = self.testRunner.run(self.test)
        finally:
            if self.runLocalServer:
                self._serverProcess.stop()
        return result
