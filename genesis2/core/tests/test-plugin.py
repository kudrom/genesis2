from unittest import TestCase

from genesis2.core.core import Plugin
from genesis2.core.tests.test_app import IFakeInterface


class TestPluginManager(TestCase):
    def setUp(self):
        class MyPlugin(Plugin):
            def __init__(self):
                super(MyPlugin, self).__init__()
                self._implements.append(IFakeInterface)

            def simple_method(self):
                pass

        self.fake_interface = IFakeInterface
        self.my_plugin = MyPlugin

    def test_incorrect_plugin(self):
        # raises PluginRequirement
        pass

    def test_abstract(self):
        # raises PluginImplementationAbstract
        pass

    def test_already(self):
        # raises PluginAlreadyImplemented
        pass

    def test_loading_plugins(self):
        # test genesis2.apis using imp.load_module(genesis2.apis) after instantiating a plugin
        # also hasattr(genesis2.apis, plugin)
        pass

    def test_singleton_plugin(self):
        pass

    # The access control is tested in integration