from unittest import TestCase
import os

from genesis2.utils.filesystem import unlink_recursive, create_files


class TestFilesystem(TestCase):
    def setUp(self):
        self.dir = os.path.dirname(__file__)
        if os.path.exists(self.dir + '/dir1/dir2/file12'):
            os.remove(self.dir + '/dir1/dir2/file12')
        if os.path.exists(self.dir + '/dir1/file1'):
            os.remove(self.dir + '/dir1/file1')
        if os.path.exists(self.dir + '/dir1/dir2'):
            os.rmdir(self.dir + '/dir1/dir2')
        if os.path.exists(self.dir + '/dir1'):
            os.rmdir(self.dir + '/dir1')
        self.assertNotIn('dir1', os.listdir(self.dir))

    def test_unlink_recursive(self):
        os.makedirs(self.dir + '/dir1/dir2/')
        open(self.dir + '/dir1/dir2/file12', 'a').close()
        open(self.dir + '/dir1/file1', 'a').close()
        unlink_recursive(self.dir + '/dir1')
        self.assertFalse(os.path.exists(self.dir + '/dir1'))

    def test_create_files(self):
        pass
