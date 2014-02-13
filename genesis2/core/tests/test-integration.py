from unittest import TestCase

from ..core import Plugin, App, Interface
from ..exceptions import AccessError
from ..pluginmgr import PluginManager


class TestDeployApp(TestCase):
    def setUp(self):
        class FakeInterface(Interface):
            def __init__(self):
                super(FakeInterface, self).__init__()
                self._required_app.append(self.required)

            def required(self):
                pass

            def simple_method(self):
                pass

        class MyApp(App):
            def __init__(self):
                super(MyApp, self).__init__()
                self._uses.append(FakeInterface)

            def required(self):
                print "Done"

        class MyPlugin(Plugin):
            def __init__(self):
                super(MyPlugin, self).__init__()
                self._implements.append(FakeInterface)

            def simple_method(self):
                pass

        self.my_app = MyApp()
        self.my_plugin = MyPlugin()
        self.fake_interface = FakeInterface

    def test_access_violation(self):
        fake_interface = self.fake_interface

        class AnotherInterface(Interface):
            pass

        class RogueApp(App):
            def __init__(self):
                self._uses.append(fake_interface)

            def required(self):
                PluginManager.grab_plugin(AnotherInterface)

        myapp = RogueApp()
        self.assertRaises(AccessError, myapp.required)

    def test_correct_access(self):
        pass
