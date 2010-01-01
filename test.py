#!/usr/bin/env python

"""Test runner.

For further help, enter this at a command prompt:

python test.py --help
"""

# Modules containing tests to run -- a test is anything named *Tests, which
# should be classes deriving from unittest.TestCase.
MODULE_NAMES = [
    "test_api",
    "test_browser",
    "test_cookies",
    "test_date",
    "test_form",
    "test_form_mutation",
    "test_headers",
    "test_html",
    "test_import",
    "test_opener",
    # "test_performance",  # too slow, run from release script
    "test_pullparser",
    "test_response",
    "test_urllib2",
    "test_useragent",
    ]

import sys, os, logging, glob


def main(argv):
    # XXX
    # temporary stop-gap to run doctests &c.
    # should switch to nose or something

    top_level_dir = os.path.dirname(os.path.abspath(argv[0]))

    use_cgitb = "-t" in argv
    if use_cgitb:
        argv.remove("-t")
    run_doctests = "-d" not in argv
    if not run_doctests:
        argv.remove("-d")
    run_unittests = "-u" not in argv
    if not run_unittests:
        argv.remove("-u")
    log = "-l" in argv
    if log:
        argv.remove("-l")
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
             _http, _rfc3986, _useragent, _urllib2_fork
        doctest.testmod(_auth)
        doctest.testmod(_clientcookie)
        doctest.testmod(_headersutil)
        doctest.testmod(_http)
        doctest.testmod(_pullparser)
        doctest.testmod(_rfc3986)
        doctest.testmod(_urllib2_fork)
        doctest.testmod(_useragent)

    if run_unittests:
        # run vanilla unittest tests
        test_path = os.path.join(os.path.dirname(argv[0]), "test")
        sys.path.insert(0, test_path)
        test_runner = None
        if use_cgitb:
            test_runner = testprogram.CgitbTextTestRunner()
        prog = testprogram.TestProgram(MODULE_NAMES, testRunner=test_runner)
        result = prog.runTests()

    # XXX exit status is wrong -- does not take account of doctests
    sys.exit(not result.wasSuccessful())


if __name__ == "__main__":
    main(sys.argv)
