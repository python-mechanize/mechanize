import unittest
import sys


class ImportTests(unittest.TestCase):

    @unittest.skipIf(sys.version_info.major >= 3, "Python . does not support import * inside functions")
    def test_import_all(self):
        # the following will raise an exception if __all__ contains undefined
        # classes
        # TODO: Check that on python 3.x
        pass
        # from mechanize import *


if __name__ == "__main__":
    unittest.main()
