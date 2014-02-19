from unittest import TestCase
from mock import patch, MagicMock, call

from genesis2.core.exceptions import AppInterfaceImplError, AppRequirementError
from genesis2.core.core import AppManager, AppInfo, App
from genesis2.core.tests.interfaces import IFakeInterface
import genesis2.apis


class TestApp(TestCase):
    def setUp(self):
        class MyApp(App):
            def __init__(self):
                super(MyApp, self).__init__()
                self._uses.append(IFakeInterface)

            def required(self):
                return "it worked"

        class MyApp2(App):
            def __init__(self):
                super(MyApp2, self).__init__()
                self._uses.append(IFakeInterface)

            def required(self):
                return "it worked"

        class MockMetadata(object):
            def __init__(self):
                self.AUTHOR = "kudrom"
                self.NAME = "Testing"
                self.DESCRIPTION = "An awesome app"
                self.HOMEPAGE = "http://www.example.com"
                self.ICON = "hello-icon"
                self.INTERFACES = ["IFakeInterface"]

        # This is only used by test_app_info
        self.metadata = MagicMock()
        self.metadata.AUTHOR = "kudrom"
        self.metadata.NAME = "Testing"
        self.metadata.DESCRIPTION = "An awesome app"
        self.metadata.HOMEPAGE = "http://www.example.com"
        self.metadata.ICON = "hello-icon"
        self.metadata.INTERFACES = [IFakeInterface]

        # Constructors
        self.my_app = MyApp
        self.my_app2 = MyApp2
        self.fake_interface = IFakeInterface

        # Initializing the appmanager
        self.appmgr = AppManager(path_apps="/".join((__file__.split("/")[:-1])) + "/apps")
        self.appmgr._metadata = MockMetadata()

        # The mocking of the app.__init__.py file
        self.mockmetadata = MockMetadata

    def tearDown(self):
        # To ensure that the loading of apps in one test doesn't misleads the results in other
        self.appmgr._instance_apps = {}
        self.appmgr._apps = {}
        self.appmgr._metadata = self.mockmetadata()

    def test_appmgr_singleton(self):
        appmgr2 = AppManager()
        self.assertEqual(self.appmgr, appmgr2)
        self.assertEqual(self.appmgr.path_apps, "/".join(__file__.split("/")[:-1]) + "/apps")

    def test_requirements_app(self):
        fake_interface = self.fake_interface

        class MyApp(App):
            def __init__(self):
                super(MyApp, self).__init__()
                self._uses.append(fake_interface)

        with self.assertRaises(AppInterfaceImplError):
            MyApp()

    def test_singleton_app(self):
        myapp = self.my_app()
        myapp2 = self.my_app()
        self.assertEqual(id(myapp), id(myapp2))

    def test_register_app(self):
        with patch('genesis2.core.core.AppManager') as manager:
            myapp = self.my_app()
            manager().register.assert_called_once_with(myapp, self.fake_interface)

    def test_observable_register(self):
        notify_observers_mock = MagicMock()
        self.appmgr.notify_observers = notify_observers_mock
        self.my_app()
        app = self.appmgr.grab_apps()[0]
        calls = [call("register", app, IFakeInterface)]
        notify_observers_mock.assert_has_calls(calls)

    def test_unregister_app(self):
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 0)

        myapp = self.my_app()
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)
        self.assertEqual(id(myapp), id(apps[0].instance))

        self.appmgr.unregister(apps[0])
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 0)

        self.my_app()
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)
        self.my_app2()
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 2)
        self.appmgr.unregister(apps[0])
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)

    def test_observable_unregister(self):
        notify_observers_mock = MagicMock()
        self.appmgr.notify_observers = notify_observers_mock

        self.my_app()
        app = self.appmgr.grab_apps()[0]
        self.appmgr.unregister(app)
        calls = [call("unregister", app, self.fake_interface)]
        notify_observers_mock.assert_has_calls(calls)

    def test_grab_apps(self):
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 0)

        myapp = self.my_app()
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 1)
        self.assertEqual(myapp.required(), "it worked")
        self.assertEqual(apps[0].instance, myapp)

        myapp2 = self.my_app2()
        apps = self.appmgr.grab_apps(self.fake_interface)
        self.assertEqual(len(apps), 2)

    def test_grab_filter(self):
        myapp = self.my_app()
        self.appmgr._metadata.AUTHOR = "PinkyWinky"
        myapp2 = self.my_app2()
        apps = self.appmgr.grab_apps(self.fake_interface, flt=lambda app: app.author == "kudrom")
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].instance, myapp)

    def test_app_info(self):
        instance = MagicMock()
        app = AppInfo(instance, self.metadata)
        self.assertEqual(app.instance, instance)
        self.assertEqual(app.author, self.metadata.AUTHOR)
        self.assertEqual(app.name, self.metadata.NAME)
        self.assertEqual(app.description, self.metadata.DESCRIPTION)
        self.assertEqual(app.homepage, self.metadata.HOMEPAGE)
        self.assertEqual(app.icon, self.metadata.ICON)
        self.assertEqual(app.interfaces, self.metadata.INTERFACES)

    def test_load_apps(self):
        load_app_mock = MagicMock()
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-1])) + "/apps"
        old_load = self.appmgr.load_app
        self.appmgr.load_app = load_app_mock
        notify_observers_mock = MagicMock()
        self.appmgr.notify_observers = notify_observers_mock
        self.appmgr.load_apps()
        calls = [call("app1"), call("app2"), call("appIntegration")]
        load_app_mock.assert_has_calls(calls, any_order=True)
        calls = [call("load_apps")]
        notify_observers_mock.assert_has_calls(calls)

        self.appmgr.load_app = old_load

    def test_load_app(self):
        old_plugin = genesis2.apis.PFakeInterface
        genesis2.apis.PFakeInterface = object()
        self.appmgr.load_app("app1")
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app.author, "kudrom")

        genesis2.apis.PFakeInterface = old_plugin

    def test_load_app_with_not_implemented_interface(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-1])) + "/test_app_apps"
        with self.assertRaises(AppRequirementError):
            self.appmgr.load_app("requirementErrorApp")
