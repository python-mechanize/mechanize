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

import mechanize
from mechanize import _headersutil, _auth, _clientcookie, _pullparser, \
    _http, _rfc3986, _useragent, _urllib2_fork


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


def mutate_sys_path():
    this_dir = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(this_dir, "test"))
    sys.path.insert(0, os.path.join(this_dir, "test-tools"))


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


class DefaultResult:

    def wasSuccessful(self):
        return True


def main(argv):
    # TODO: switch to nose or something

    mutate_sys_path()
    # test-tools/ dir includes a bundled Python 2.5 doctest / linecache -- this
    # is only for testing purposes, these don't get installed
    # doctest.py revision 45701 and linecache.py revision 45940.  Since
    # linecache is used by Python itself, linecache.py is renamed
    # linecache_copy.py, and this copy of doctest is modified (only) to use
    # that renamed module.
    assert "doctest" not in sys.modules
    import doctest  # bundled copy
    import testprogram

    options, remaining_args = parse_options(argv[1:])

    if options.log:
        level = logging.DEBUG
#         level = logging.INFO
#         level = logging.WARNING
#         level = logging.NOTSET
        logger = logging.getLogger("mechanize")
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        logger.addHandler(handler)

    result = DefaultResult()

    if options.run_doctests:
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

        # run .doctest files
        doctest_files = glob.glob(os.path.join("test", "*.doctest"))
        for df in doctest_files:
            doctest.testfile(df)

        # run doctests in docstrings
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
