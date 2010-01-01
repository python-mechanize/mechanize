#!/usr/bin/env python

"""Test runner.

For further help, enter this at a command prompt:

python test.py --help
"""

import glob
import logging
import optparse
import os
import sys


# Modules containing tests to run
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


def parse_options(args):
    parser = optparse.OptionParser(usage=__doc__.rstrip())
    parser.add_option("--cgitb")
    parser.add_option("-d", "--skip-doctests",
                      default=True, action="store_false", dest="run_doctests")
    parser.add_option("-u", "--skip-vanilla",
                      default=True, action="store_false", dest="run_vanilla",
                      help="Skip vanilla unittest tests")
    parser.add_option("--log",
                      help=('Turn on logging for logger "mechanize" at level '
                            'logging.DEBUG'))
    return parser.parse_args(args)


def main(argv):
    # XXX
    # temporary stop-gap to run doctests &c.
    # should switch to nose or something
    options, remaining_args = parse_options(argv[1:])

    # use_cgitb = "-t" in argv
    # if use_cgitb:
    #     argv.remove("-t")
    # run_doctests = "-d" not in argv
    # if not run_doctests:
    #     argv.remove("-d")
    # run_unittests = "-u" not in argv
    # if not run_unittests:
    #     argv.remove("-u")
    # log = "-l" in argv
    if options.log:
        # argv.remove("-l")
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

    if options.run_doctests:
        print "yup"
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

    if options.run_vanilla:
        # run vanilla unittest tests
        test_path = os.path.join(os.path.dirname(argv[0]), "test")
        sys.path.insert(0, test_path)
        test_runner = None
        if options.cgitb:
            test_runner = testprogram.CgitbTextTestRunner()
        prog = testprogram.TestProgram(MODULE_NAMES,
                                       argv=[argv[0]] + remaining_args,
                                       testRunner=test_runner)
        result = prog.runTests()

    # XXX exit status is wrong -- does not take account of doctests
    sys.exit(not result.wasSuccessful())


if __name__ == "__main__":
    main(sys.argv)
