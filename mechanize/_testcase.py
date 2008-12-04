import shutil
import tempfile
import unittest


class TestCase(unittest.TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self._on_teardown = []

    def make_temp_dir(self):
        temp_dir = tempfile.mkdtemp(prefix="tmp-%s-" % self.__class__.__name__)
        def tear_down():
            shutil.rmtree(temp_dir)
        self._on_teardown.append(tear_down)
        return temp_dir

    def monkey_patch(self, obj, name, value):
        orig_value = getattr(obj, name)
        setattr(obj, name, value)
        def reverse_patch():
            setattr(obj, name, orig_value)
        self._on_teardown.append(reverse_patch)

    def assert_contains(self, container, containee):
        self.assertTrue(containee in container, "%r not in %r" %
                        (containee, container))

    def tearDown(self):
        for func in reversed(self._on_teardown):
            func()
