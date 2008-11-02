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

import sys, os, logging, glob


if __name__ == "__main__":
    # XXX
    # temporary stop-gap to run doctests &c.
    # should switch to nose or something

    top_level_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # XXXX coverage output seems incorrect ATM
    run_coverage = "-c" in sys.argv
    if run_coverage:
        sys.argv.remove("-c")
    use_cgitb = "-t" in sys.argv
    if use_cgitb:
        sys.argv.remove("-t")
    run_doctests = "-d" not in sys.argv
    if not run_doctests:
        sys.argv.remove("-d")
    run_unittests = "-u" not in sys.argv
    if not run_unittests:
        sys.argv.remove("-u")
    log = "-l" in sys.argv
    if log:
        sys.argv.remove("-l")
        level = logging.DEBUG
#         level = logging.INFO
#         level = logging.WARNING
#         level = logging.NOTSET
        logger = logging.getLogger("mechanize")
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        logger.addHandler(handler)

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
    import testprogram

    if run_coverage:
        import coverage
        print 'running coverage'
        coverage.erase()
        coverage.start()

    import mechanize

    class DefaultResult:
        def wasSuccessful(self):
            return True
    result = DefaultResult()

    if run_doctests:
        # run .doctest files needing special support
        common_globs = {"mechanize": mechanize}
        pm_doctest_filename = os.path.join(
            "test", "test_password_manager.special_doctest")
        for globs in [
            {"mgr_class": mechanize.HTTPPasswordMgr},
            {"mgr_class": mechanize.HTTPProxyPasswordMgr},
            ]:
            globs.update(common_globs)
            doctest.testfile(pm_doctest_filename, globs=globs)
        try:
            import robotparser
        except ImportError:
            pass
        else:
            doctest.testfile(os.path.join(
                    "test", "test_robotfileparser.special_doctest"))

        # run .doctest files
        doctest_files = glob.glob(os.path.join("test", "*.doctest"))
        for df in doctest_files:
            doctest.testfile(df)

        # run doctests in docstrings
        from mechanize import _headersutil, _auth, _clientcookie, _pullparser, \
             _http, _rfc3986, _useragent
        doctest.testmod(_headersutil)
        doctest.testmod(_rfc3986)
        doctest.testmod(_auth)
        doctest.testmod(_clientcookie)
        doctest.testmod(_pullparser)
        doctest.testmod(_http)
        doctest.testmod(_useragent)

    if run_unittests:
        # run vanilla unittest tests
        import unittest
        test_path = os.path.join(os.path.dirname(sys.argv[0]), "test")
        sys.path.insert(0, test_path)
        test_runner = None
        if use_cgitb:
            test_runner = testprogram.CgitbTextTestRunner()
        prog = testprogram.TestProgram(
            MODULE_NAMES,
            testRunner=test_runner,
            localServerProcess=testprogram.TwistedServerProcess(),
            )
        result = prog.runTests()

    if run_coverage:
        # HTML coverage report
        import colorize
        try:
            os.mkdir("coverage")
        except OSError:
            pass
        private_modules = glob.glob("mechanize/_*.py")
        private_modules.remove("mechanize/__init__.py")
        for module_filename in private_modules:
            module_name = module_filename.replace("/", ".")[:-3]
            print module_name
            module = sys.modules[module_name]
            f, s, m, mf = coverage.analysis(module)
            fo = open(os.path.join('coverage', os.path.basename(f)+'.html'), 'wb')
            colorize.colorize_file(f, outstream=fo, not_covered=mf)
            fo.close()
            coverage.report(module)
            #print coverage.analysis(module)

    # XXX exit status is wrong -- does not take account of doctests
    sys.exit(not result.wasSuccessful())
