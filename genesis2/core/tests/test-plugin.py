from unittest import TestCase

from ..core import Interface, Plugin
from ..pluginmgr import PluginManager


class TestPluginManager(TestCase):
    def setUp(self):
        class FakeInterface(Interface):
            def __init__(self):
                super(FakeInterface, self).__init__()
                self._required_app.append(self.required)

            def required(self):
                pass

            def simple_method(self):
                pass

        class MyPlugin(Plugin):
            def __init__(self):
                super(MyPlugin, self).__init__()
                self._implements.append(FakeInterface)

            def simple_method(self):
                pass

        self.fake_interface = FakeInterface
        self.my_plugin = MyPlugin

    def test_incorrect_plugin(self):
        """
         Si interesa
        """

    def test_pluginmanager(self):
        pass

    def test_unique_plugin(self):
        pass

    def test_multiple_plugin(self):
        pass

    def test_verify_dep(self):
        pass
