#!/usr/bin/env python

"""
Note that the functional tests and doctests require test-tools to be on
sys.path.  One way to ensure that is to use this script to run tests.

Usage examples:

python test.py  # all tests
python test.py test_api  # run test/test_api.py
python test.py functional_tests  # run test/functional_tests.py
python test.py mechanize/_headersutil  # run the doctests from this module
python test.py functional_tests.CookieJarTests  # just this class
# just this test method
python test.py functional_tests.CookieJarTests.test_mozilla_cookiejar

python test.py discover --pattern test_browser.doctest  # doctest file
# run test/functional_tests.py
python test.py discover --pattern functional_tests.py
"""

import os
import sys


def mutate_sys_path():
    this_dir = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(this_dir, "test"))
    sys.path.insert(0, os.path.join(this_dir, "test-tools"))


def main(argv):
    # test-tools/ dir includes a bundled Python 2.5 doctest / linecache, and a
    # bundled & modified Python trunk (2.7 vintage) unittest.  This is only for
    # testing purposes, and these don't get installed.

    # unittest revision 77209, modified

    # doctest.py revision 45701 and linecache.py revision 45940.  Since
    # linecache is used by Python itself, linecache.py is renamed
    # linecache_copy.py, and this copy of doctest is modified (only) to use
    # that renamed module.

    mutate_sys_path()
    assert "doctest" not in sys.modules
    import testprogram

    # *.py to catch doctests in docstrings
    this_dir = os.path.dirname(__file__)
    prog = testprogram.TestProgram(
        argv=argv, default_discovery_args=(this_dir, "*.py", None),
        module=None)
    result = prog.runTests()
    success = result.wasSuccessful()
    sys.exit(int(not success))


if __name__ == "__main__":
    main(sys.argv)
