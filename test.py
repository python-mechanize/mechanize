#!/usr/bin/env python

"""Test runner.

For further help, enter this at a command prompt:

python test.py --help

"""

# Modules containing tests to run -- a test is anything named *Tests, which
# should be classes deriving from unittest.TestCase.
MODULE_NAMES = ["test_date", "test_browser", "test_response", "test_cookies",
                "test_headers", "test_urllib2", "test_pullparser",
                "test_useragent", "test_html", "test_opener",
                ]

import sys, os, traceback, logging, glob
from unittest import defaultTestLoader, TextTestRunner, TestSuite, TestCase

level = logging.DEBUG
#level = logging.INFO
#level = logging.NOTSET
#logging.getLogger("mechanize").setLevel(level)

class TestProgram:
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = """\
Usage: %(progName)s [options] [test] [...]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output

Examples:
  %(progName)s                               - run default set of tests
  %(progName)s MyTestSuite                   - run suite 'MyTestSuite'
  %(progName)s MyTestCase.testSomething      - run MyTestCase.testSomething
  %(progName)s MyTestCase                    - run all 'test*' test methods
                                               in MyTestCase
"""
    def __init__(self, moduleNames, defaultTest=None,
                 argv=None, testRunner=None, testLoader=defaultTestLoader):
        self.modules = []
        for moduleName in moduleNames:
            module = __import__(moduleName)
            for part in moduleName.split('.')[1:]:
                module = getattr(module, part)
            self.modules.append(module)
        if argv is None:
            argv = sys.argv
        self.verbosity = 1
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.parseArgs(argv)

    def usageExit(self, msg=None):
        if msg: print msg
        print self.USAGE % self.__dict__
        sys.exit(2)

    def parseArgs(self, argv):
        import getopt
        try:
            options, args = getopt.getopt(argv[1:], 'hHvq',
                                          ['help','verbose','quiet'])
            for opt, value in options:
                if opt in ('-h','-H','--help'):
                    self.usageExit()
                if opt in ('-q','--quiet'):
                    self.verbosity = 0
                if opt in ('-v','--verbose'):
                    self.verbosity = 2
            if len(args) == 0 and self.defaultTest is None:
                suite = TestSuite()
                for module in self.modules:
                    test = self.testLoader.loadTestsFromModule(module)
                    suite.addTest(test)
                self.test = suite
                return
            if len(args) > 0:
                self.testNames = args
            else:
                self.testNames = (self.defaultTest,)
            self.createTests()
        except getopt.error, msg:
            self.usageExit(msg)

    def createTests(self):
        self.test = self.testLoader.loadTestsFromNames(self.testNames)

    def runTests(self):
        if self.testRunner is None:
            self.testRunner = TextTestRunner(verbosity=self.verbosity)
        result = self.testRunner.run(self.test)
        return result


if __name__ == "__main__":
##     sys.path.insert(0, '/home/john/comp/dev/rl/jjlee/lib/python')
##     import jjl
##     import __builtin__
##     __builtin__.jjl = jjl

    # XXX temporary stop-gap to run doctests

    # XXXX coverage output seems incorrect ATM
    run_coverage = '-c' in sys.argv
    if run_coverage:
        sys.argv.remove("-c")

    # import local copy of Python 2.5 doctest
    assert os.path.isdir("test")
    sys.path.insert(0, "test")
    # needed for recent doctest / linecache -- this is only for testing
    # purposes, these don't get installed
    # doctest.py revision 45701 and linecache.py revision 45940.  Since
    # linecache is used by Python itself, linecache.py is renamed
    # linecache_copy.py, and this copy of doctest is modified (only) to use
    # that renamed module.
    sys.path.insert(0, "test-tools")
    import doctest

    import coverage
    if run_coverage:
        print 'running coverage'
        coverage.erase()
        coverage.start()

    import mechanize

    # run .doctest files needing special support
    common_globs = {"mechanize": mechanize}
    pm_doctest_filename = os.path.join("test", "test_password_manager.doctest")
    for globs in [
        {"mgr_class": mechanize.HTTPPasswordMgr},
        {"mgr_class": mechanize.HTTPProxyPasswordMgr},
        ]:
        globs.update(common_globs)
        doctest.testfile(
            pm_doctest_filename,
            #os.path.join("test", "test_scratch.doctest"),
            globs=globs,
            )

    # run .doctest files
    special_doctests = [pm_doctest_filename,
                        os.path.join("test", "test_scratch.doctest"),
                        ]
    doctest_files = glob.glob(os.path.join("test", "*.doctest"))

    for dt in special_doctests:
        if dt in doctest_files:
            doctest_files.remove(dt)
    for df in doctest_files:
        doctest.testfile(df)

    # run doctests in docstrings
    from mechanize import _headersutil, _auth, _clientcookie, _pullparser, \
         _http
    doctest.testmod(_headersutil)
    doctest.testmod(_auth)
    doctest.testmod(_clientcookie)
    doctest.testmod(_pullparser)
    doctest.testmod(_http)

    # run vanilla unittest tests
    import unittest
    test_path = os.path.join(os.path.dirname(sys.argv[0]), "test")
    sys.path.insert(0, test_path)
    prog = TestProgram(MODULE_NAMES)
    result = prog.runTests()

    if run_coverage:
        # HTML coverage report
        import colorize
        from mechanize import _mechanize
        try:
            os.mkdir("coverage")
        except OSError:
            pass
        f, s, m, mf = coverage.analysis(_mechanize)
        fo = open(os.path.join('coverage', os.path.basename(f)+'.html'), 'wb')
        colorize.colorize_file(f, outstream=fo, not_covered=mf)
        fo.close()
        coverage.report(_mechanize)
        #print coverage.analysis(_mechanize)

    # XXX exit status is wrong -- does not take account of doctests
    sys.exit(not result.wasSuccessful())
