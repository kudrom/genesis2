from unittest import TestCase
from mock import patch

from ..core import App, Interface
from ..exceptions import AppInterfaceImplError
from ..appmgr import AppManager


class TestApp(TestCase):
    def setUp(self):
        class FakeInterface(Interface):
            def __init__(self):
                self._required_app = self.required

            def required(self):
                pass

            def non_required(self):
                pass

        class MyApp(App):
            def __init__(self):
                self._uses.append(FakeInterface)

            def required(self):
                return "it worked"

        self.my_app = MyApp
        self.fake_interface = FakeInterface
        self.appmgr = AppManager(path_apps=)

    def test_requirements_app(self):
        fake_interface = self.fake_interface

        def aux():
            class MyApp(App):
                def __init__(self):
                    self._uses.append(fake_interface)

        self.assertRaises(AppInterfaceImplError, aux)

    def test_singleton_app(self):
        myapp = self.my_app()
        myapp2 = self.my_app()
        self.assertEqual(id(myapp), id(myapp2))

    def test_register_app(self):
        with patch('..appmgr.AppManager') as manager:
            myapp = self.my_app()
            manager.register.assert_called_once_with(myapp, self.fake_interface)

    def test_unregister_app(self):
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 0)
        myapp = self.my_app()
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)
        self.appmgr.unregister(myapp)
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 0)

    def test_grab_apps(self):
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 0)

        myapp = self.my_app()
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 1)
        self.assertEqual(myapp.required(), "it worked")
        self.assertEqual(apps[0], myapp)

        myapp2 = self.my_app()
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 2)
        self.assertIn(myapp2, apps)
        self.assertIn(myapp, apps)

    def test_grab_filter(self):
        # Authored by kudrom
        class MyApp2(self.myapp):
            pass

        myapp1 = self.my_app()
        myapp2 = MyApp2()
        apps = self.appmgr.grab_apps(self.fake_interface, flt=lambda app: app.author == "kudrom")
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0], myapp2)

    def test_app_info(self):
        pass

    def test_load_apps(self):
        pass

    def test_load_app(self):
        pass
