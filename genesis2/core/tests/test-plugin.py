from unittest import TestCase

from genesis2.core.core import Plugin
from genesis2.core.utils import Interface
from genesis2.core.tests.test_app import IFakeInterface
from genesis2.core.exceptions import PluginInterfaceImplError, PluginImplementationAbstract, PluginAlreadyImplemented, \
    AccessDenied
from genesis2.core.core import AppManager
import genesis2.apis


class TestPluginManager(TestCase):
    def setUp(self):
        class MyPlugin(Plugin):
            def __init__(self):
                super(MyPlugin, self).__init__()
                self._implements.append(IFakeInterface)

            def non_required(self):
                return "it works"

            def non_protected(self):
                return "it's not protected"

        self.fake_interface = IFakeInterface
        self.my_plugin = MyPlugin
        self.appmgr = AppManager(path_apps="/".join((__file__.split("/")[:-1])) + "/apps")

    def tearDown(self):
        if hasattr(genesis2.apis, "PFakeInterface"):
            del genesis2.apis.PFakeInterface

    def test_incorrect_plugin(self):
        class MyPlugin2(Plugin):
            def __init__(self):
                super(MyPlugin2, self).__init__()
                self._implements.append(IFakeInterface)
        with self.assertRaises(PluginInterfaceImplError):
            MyPlugin2()

    def test_abstract(self):
        class IAbstract(Interface):
            def __init__(self):
                super(IAbstract, self).__init__()
                self.abstract = True

        class MyPlugin2(Plugin):
            def __init__(self):
                super(MyPlugin2, self).__init__()
                self._implements.append(IAbstract)

        with self.assertRaises(PluginImplementationAbstract):
            MyPlugin2()

    def test_already(self):
        setattr(genesis2.apis, "PFakeInterface", object())
        with self.assertRaises(PluginAlreadyImplemented):
            self.my_plugin()

    def test_loading_plugins(self):
        self.my_plugin()
        self.assertTrue(hasattr(genesis2.apis, "PFakeInterface"))

    def test_normal_access(self):
        ret = self.my_plugin().non_protected()
        self.assertEqual(ret, "it's not protected")

    def test_protected_access_scope(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-1])) + "/apps"
        ret = self.my_plugin().non_required()
        self.assertEqual(ret, "it works")

    def test_whitout_uses_protected_access(self):
        self.appmgr.path_apps =  "/".join((__file__.split("/")[:-1]))
        with self.assertRaises(AccessDenied):
            self.my_plugin().non_required()

    def test_with_invalid_uses_protected_access(self):
        self.appmgr.path_apps =  "/".join((__file__.split("/")[:-1]))
        self._uses = []
        with self.assertRaises(AccessDenied):
            self.my_plugin().non_required()

    def test_protected_access(self):
        self.appmgr.path_apps =  "/".join((__file__.split("/")[:-1]))
        self._uses = [IFakeInterface]
        ret = self.my_plugin().non_required()
        self.assertEqual(ret, "it works")

    def test_outer_scope_protected_access(self):
        self.appmgr.path_apps =  "/".join((__file__.split("/")[:-1]))
        with self.assertRaises(TypeError):
            outer_scope()


def outer_scope():
    class MyPlugin(Plugin):
        def __init__(self):
            super(MyPlugin, self).__init__()
            self._implements.append(IFakeInterface)

        def non_required(self):
            pass

    myplugin = MyPlugin()
    myplugin.non_required()
