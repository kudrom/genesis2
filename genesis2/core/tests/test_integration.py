from unittest import TestCase

from genesis2.core.core import AppManager
from genesis2.core.tests.interfaces import IFakeInterface, IAnotherInterface
from genesis2.core.exceptions import AccessDenied

"""
All of these tests might fail if <from genesis2.core.tests.plugins import *> was called before due to the
impossibility to unload a module in python (http://bugs.python.org/issue9072)
"""
from genesis2.core.tests.plugins import *


class TestNormalUse(TestCase):
    def setUp(self):
        self.appmgr = AppManager()
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-1])) + "/apps"
        self.appmgr.load_apps()

    def test_app_plugin(self):
        apps = self.appmgr.grab_apps(IFakeInterface, flt=lambda app: app.instance.__class__.__name__ == "IntegrationApp")
        self.assertEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app.instance.required(), "fucking awesome: I agree")

    def test_app_plugin_control_access(self):
        apps = self.appmgr.grab_apps(IAnotherInterface)
        self.assertEqual(len(apps), 1)
        app = apps[0]
        with self.assertRaises(AccessDenied):
            app.instance.required()
