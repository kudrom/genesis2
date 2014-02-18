from unittest import TestCase

from genesis2.launcher import run_server

"""
I'm not going to test the logging system because i presume that it's already well tested and the log config can change
from one developer environment to another, so it would be quite useless to see that some tests fail because the
logging config is different to the default.
"""


class TestDirConfigs(TestCase):
    pass


class TestRunServer(TestCase):
    def test_something(self):
        run_server()
