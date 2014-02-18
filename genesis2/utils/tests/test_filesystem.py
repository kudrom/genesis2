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

    def test_create_files_base_dir(self):
        current_dir = os.path.dirname(__file__)
        create_files('/dir1/file1', 'dir1/dir2/file12', base_dir=os.path.dirname(__file__))
        self.assertIn('dir1', os.listdir(current_dir))
        self.assertIn('file1', os.listdir(os.path.join(current_dir, 'dir1')))
        self.assertIn('dir2', os.listdir(os.path.join(current_dir, 'dir1')))
        self.assertIn('file12', os.listdir(os.path.join(current_dir, 'dir1/dir2')))

    def test_create_files(self):
        current_dir = os.path.dirname(__file__)
        create_files(os.path.join(current_dir, 'dir1/file1'))
        self.assertIn('dir1', os.listdir(current_dir))
        self.assertIn('file1', os.listdir(os.path.join(current_dir, 'dir1')))

    def test_create_files_without_leading_slash(self):
        current_dir = os.path.dirname(__file__)
        create_files('vagrant/genesis2/utils/tests/dir1/dir2/file12')
        self.assertIn('dir2', os.listdir(os.path.join(current_dir, 'dir1')))
        self.assertIn('file12', os.listdir(os.path.join(current_dir, 'dir1/dir2')))
