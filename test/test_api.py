import unittest


class ImportTests(unittest.TestCase):

    def test_import_all(self):
        # the following will raise an exception if __all__ contains undefined
        # classes
        import mechanize
        from mechanize import __all__
        for x in __all__:
            getattr(mechanize, x)


if __name__ == "__main__":
    unittest.main()
