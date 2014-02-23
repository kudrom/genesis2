import os
import gc
from unittest import TestCase
from mock import patch, MagicMock, call

from genesis2.core.exceptions import AppInterfaceImplError, AppRequirementError, AccessDenied, \
    PluginInterfaceImplError, PluginAlreadyImplemented, PluginImplementationAbstract

from genesis2.core.core import AppManager, AppInfo, App, PluginLoader, Plugin
from genesis2.core.utils import Observable, Interface
from genesis2.core.tests.interfaces import IFakeInterface, IAnotherInterface
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

        # Mocks the package/module metadata
        class MockMetadata(object):
            def __init__(self):
                self.AUTHOR = "kudrom"
                self.PKGNAME = "Testing"
                self.VERSION = 'v1.1'
                self.DESCRIPTION = "An awesome app"
                self.HOMEPAGE = "http://www.example.com"
                self.ICON = "hello-icon"

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
        class AppTesting(object):
            def __init__(self):
                self._uses = [IFakeInterface]
        instance = AppTesting()
        metadata = self.mockmetadata()
        app = AppInfo(instance, metadata)
        self.assertEqual(app.instance, instance)
        self.assertEqual(app.author, metadata.AUTHOR)
        self.assertEqual(app.pkgname, metadata.PKGNAME)
        self.assertEqual(app.version, metadata.VERSION)
        self.assertEqual(app.name, 'AppTesting')
        self.assertEqual(app.description, metadata.DESCRIPTION)
        self.assertEqual(app.homepage, metadata.HOMEPAGE)
        self.assertEqual(app.icon, metadata.ICON)
        self.assertEqual(app.interfaces, [IFakeInterface])

    def test_app_info_name(self):
        class AppTesting(object):
            def __init__(self):
                self._uses = [IFakeInterface]
                self.NAME = 'RandomName'
        instance = AppTesting()
        metadata = self.mockmetadata()
        app = AppInfo(instance, metadata)
        self.assertEqual(app.instance, instance)
        self.assertEqual(app.author, metadata.AUTHOR)
        self.assertEqual(app.pkgname, metadata.PKGNAME)
        self.assertEqual(app.version, metadata.VERSION)
        self.assertEqual(app.name, 'RandomName')
        self.assertEqual(app.description, metadata.DESCRIPTION)
        self.assertEqual(app.homepage, metadata.HOMEPAGE)
        self.assertEqual(app.icon, metadata.ICON)
        self.assertEqual(app.interfaces, [IFakeInterface])

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
        genesis2.apis.PFakeInterface = object()
        self.appmgr.load_app("app1")
        apps = self.appmgr.grab_apps()
        self.assertEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app.author, "kudrom")

        del genesis2.apis.PFakeInterface

    def test_load_app_with_not_implemented_interface(self):
        self.appmgr.path_apps = os.path.join(os.path.dirname(__file__), "test_app_apps")
        with self.assertRaises(AppRequirementError):
            self.appmgr.load_app("requirementErrorApp")


class TestIntegration(TestCase):
    def setUp(self):
        plugin_loader = PluginLoader()
        plugin_loader.load_plugins('genesis2/core/tests')
        self.appmgr = AppManager("/".join((__file__.split("/")[:-1])) + "/apps")
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-1])) + "/apps"
        self.appmgr.load_apps()

    def test_app_plugin(self):
        apps = self.appmgr.grab_apps(IFakeInterface, flt=lambda app: app.name == "IntegrationApp")
        self.assertEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app.instance.required(), "fucking awesome: I agree")

    def test_app_plugin_control_access(self):
        apps = self.appmgr.grab_apps(IAnotherInterface)
        self.assertEqual(len(apps), 1)
        app = apps[0]
        with self.assertRaises(AccessDenied):
            app.instance.required()


class TestObservable(TestCase):
    def setUp(self):
        class Observable1(Observable):
            def important_method(self):
                self.notify_observers("message", "argument")

        class Observer(object):
            def __init__(self):
                self.messages = []

        self.observer = Observer
        self.observable = Observable1

    def test_add_observer(self):
        observable = self.observable()
        observer = self.observer()
        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 0)

        observer.notify = MagicMock()
        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)

    def test_notify(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()
        observable.add_observer(observer)

        observable.important_method()
        observer.notify.assert_called_once_with(observable, "message", "argument")

    def test_remove(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()

        ref = observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)
        observable.remove_observer(ref)
        self.assertEqual(observable.get_n_observers(), 0)

        # Just in case
        observable.remove_observer(ref)

    def test_weak(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()

        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)

        del observer
        gc.collect()
        self.assertEqual(observable.get_n_observers(), 0)


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

        if hasattr(genesis2.apis, 'PFakeInterface'):
            TestPluginManager.old_PFakeInterface = genesis2.apis.PFakeInterface
        if hasattr(genesis2.apis, 'PAnotherInterface'):
            TestPluginManager.old_PAnotherInterface = genesis2.apis.PAnotherInterface

        self.fake_interface = IFakeInterface
        self.my_plugin = MyPlugin
        self.appmgr = AppManager(path_apps="/".join((__file__.split("/")[:-2])) + "/apps")

    def tearDown(self):
        if hasattr(genesis2.apis, "PFakeInterface"):
            del genesis2.apis.PFakeInterface
        if hasattr(genesis2.apis, "PAnotherInterface"):
            del genesis2.apis.PAnotherInterface

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
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-2])) + "/apps"
        ret = self.my_plugin().non_required()
        self.assertEqual(ret, "it works")

    def test_whitout_uses_protected_access(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-2]))
        with self.assertRaises(AccessDenied):
            self.my_plugin().non_required()

    def test_with_invalid_uses_protected_access(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-2]))
        self._uses = []
        with self.assertRaises(AccessDenied):
            self.my_plugin().non_required()

    def test_protected_access(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-2]))
        self._uses = [IFakeInterface]
        ret = self.my_plugin().non_required()
        self.assertEqual(ret, "it works")

    def test_outer_scope_protected_access(self):
        self.appmgr.path_apps = "/".join((__file__.split("/")[:-2]))
        with self.assertRaises(TypeError):
            outer_scope()

    def test_loader(self):
        """
        The old_PFakeInterface thing ensures that genesis2.apis is registered with the correct plugin.
        That's because genesis2.core.tests.plugins are already loaded but in teardown i deleted the genesis2.apis
        entries to reset the side effects of the other tests, so sys.modules has the genesis2.core.tests.plugins loaded
        and it's impossible to rerun the bunch of __init__.py that would trigger the storing of the plugins in the apis
        (reload doesn't do that by design).
        """
        pluginloader = PluginLoader()
        pluginloader.load_plugins('genesis2/core/tests')
        # Reset the registered plugins
        if hasattr(TestPluginManager, 'old_PFakeInterface'):
            genesis2.apis.PFakeInterface = TestPluginManager.old_PFakeInterface
        if hasattr(TestPluginManager, 'old_PAnotherInterface'):
            genesis2.apis.PAnotherInterface = TestPluginManager.old_PAnotherInterface

        self.assertTrue(hasattr(genesis2.apis, "PFakeInterface"))
        ret = genesis2.apis.PFakeInterface.non_required()
        self.assertEqual(ret, "fucking awesome")


def outer_scope():
    class MyPlugin(Plugin):
        def __init__(self):
            super(MyPlugin, self).__init__()
            self._implements.append(IFakeInterface)

        def non_required(self):
            pass

    myplugin = MyPlugin()
    myplugin.non_required()
