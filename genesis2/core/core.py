import imp
import os
import inspect
import logging
from types import FunctionType

from genesis2.core.utils import Singleton, Observable
from genesis2.halter import stop_server
from genesis2.core.exceptions import AppRequirementError, BaseRequirementError, \
    ModuleRequirementError, AppInterfaceImplError, PluginAlreadyImplemented, PluginImplementationAbstract, \
    PluginInterfaceImplError, AccessDenied
import genesis2.apis


class MetaPlugin (Singleton):
    """
    Metaclass for Plugin that:
        - Ensures that a plugin doesn't already implements one of the interfaces (PluginAlreadyImplemented)
        - Ensures that one of the interfaces that tries to implement isn't abstract (PluginImplementationAbstract)
        - Ensures that a plugin implements the methods of the interface that aren't required by the app and aren't
          private (PluginInterfaceImplError)
        - Registers the plugin in genesis2.apis with the proper notation (the name of the interface it implements
          with the first I replaced by a P)
    """

    @staticmethod
    def _access_control(func, instance):
        """
        Method to control the access to the Plugin's methods, right now only exists an App policy that will deny every
        access made by an App that doesn't _uses the interface that the Plugin _implements.
        """
        def decorator(*args, **kwargs):
            path_apps = AppManager().path_apps
            caller_frame = inspect.stack()[1][0]
            caller_path = caller_frame.f_code.co_filename
            caller_locals = caller_frame.f_locals

            if caller_path.startswith(path_apps):
                if 'self' in caller_locals:
                    caller = caller_locals['self']
                    if hasattr(caller, "_uses"):
                        for interface in caller._uses:
                            interfaces = instance._implements
                            if interface in interfaces:
                                return func(*args, **kwargs)
                    raise AccessDenied(caller.__class__.__name__, func.__name__)
                else:
                    raise TypeError("A plugin can only be accessed inside a method by an App.")
            return func(*args, **kwargs)

        return decorator

    def __call__(cls, *args, **kwargs):
        """
        Called every time that a Plugin is instantiated.
        This method ensures that:
            - The plugin implements the proper methods of Interface (PluginInterfaceImplError)
            - The plugin is not already registered in genesis2.apis (PluginAlreadyImplemented)
            - The plugin doesn't implements any abstract interface (PluginImplementationAbstract)
        This method makes:
            - The plugin available in genesis2.apis
            - Access-control aware to all of the methods that must be implemented by the plugin, decorating them with
              _access_control
        """
        instance = super(MetaPlugin, cls).__call__(*args, **kwargs)
        for interface in instance._implements:
            plugin = "P" + interface.__name__[1:]
            if hasattr(genesis2.apis, plugin):
                name_already = getattr(genesis2.apis, plugin).__class__.__name__
                raise PluginAlreadyImplemented(plugin, interface.__name__, name_already)
            if hasattr(interface(), "abstract") and getattr(interface(), "abstract"):
                raise PluginImplementationAbstract(plugin, interface.__name__)

            methods = [method for method in dir(interface) if not method.startswith("_")
                       if method not in interface()._app_requirements]
            for method in methods:
                if method not in dir(instance):
                    raise PluginInterfaceImplError(instance.__class__.__name__, interface.__name__, method)
                # Decorate all the methods to protect them against rogue access by Apps
                decorated = MetaPlugin._access_control(getattr(instance, method), instance)
                setattr(instance, method, decorated)

            # Store it
            setattr(genesis2.apis, plugin, instance)

        return instance


class Plugin (object):
    """
    Base class for all plugins.
    Every Plugin is a singleton (see MetaPlugin  (inherits Singleton))
    """

    __metaclass__ = MetaPlugin

    def __init__(self):
        self._implements = []

        # Metadata
        self.name = ''
        self.pkgname = ''
        self.version = ''
        self.author = ''
        self.homepage = ''

    def unload(self):
        """
        Called when plugin class is being unloaded by the installer plugin.
        """


class PluginLoader(object):
    """
    Load the plugins in a directory.
    """
    __metaclass__ = Singleton

    def __init__(self):
        # Only a call per launcher is allowed to avoid the hot-install of plugins
        self.__called = False

    def load_plugins(self, dir='genesis2', config_path='configs/genesis2.conf'):
        if self.__called is False:
            logger = logging.getLogger('genesis2')
            plugins_dir = os.path.join(os.getcwd(), dir)
            plugins_module = imp.load_module('plugins', *imp.find_module('plugins', [plugins_dir]))
            # This is used by the GenesisConf plugin, to see why read the docs.
            setattr(plugins_module, 'config_path', config_path)
            if hasattr(plugins_module, 'PLUGINS'):
                for plugin in plugins_module.PLUGINS:
                    try:
                        imp.load_module(plugin, *imp.find_module(plugin, plugins_module.__path__))
                    except ImportError:
                        logger.warning('Plugin %s cannot be loaded in %s' % (plugin, plugins_dir))
            else:
                logger.error('PLUGINS attribute is missing in %s' % plugins_dir)
            self.__called = True


class AppRegister(object):
    """
    This class is only used by MetaApp.__new__ and is a Proxy to AppManager due to the python import system.

    Explanation:
    The call to register_class is made when the module is loading (it's executed when the App class is loading by
    MetaApp (its metaclass)); if i put the register_class method in AppManager (which would be the ideal solution)
    the call to the hypothetical AppManager().register would be executed when the AppManager isn't defined
    in the module's namespace, and therefore an ImportError would be raised.
    The call to register_class is necessary because i need to register the App's classes while the app modules are
    being loaded to later make an instance of these classes (see load_app, it's more or less the same mechanism that
    is used in the old genesis).
    """
    __metaclass__ = Singleton

    def __init__(self):
        self._classes = []

    def register_class(self, cls):
        if cls.__name__ != "App":
            self._classes.append(cls)


class MetaApp(Singleton):
    """
    This metaclass:
       - Ensures that the App implements all the methods that the Interface requires (_app_requirements)
       - Register the instance (__call__) in the AppManager class
       - Register the class (__new__) in the AppRegister class (which is only a proxy to AppManager)
       - Ensures that each App is only instantiated one time (see Singleton)
    """
    def __call__(cls, *args, **kwargs):
        """
        Called each time that an App's object is created
        """
        instance = super(MetaApp, cls).__call__(*args, **kwargs)
        methods = dir(instance)
        for interface in instance._uses:
            requirements = interface()._app_requirements
            for requirement in requirements:
                if requirement not in methods:
                    raise AppInterfaceImplError(instance.__class__.__name__, interface.__name__, requirement)
        AppManager().register(instance, *instance._uses)
        return instance

    def __new__(cls, *args, **kwargs):
        """
        Called each time that a class inherits from App
        """
        new_class = type.__new__(cls, *args, **kwargs)
        AppRegister().register_class(new_class)
        return new_class


class App(object):
    """
    This is the main class that arkOS developers will inherit to access the plugins provided by genesis's plugins
    """
    __metaclass__ = MetaApp

    def __init__(self):
        """
        All the subsequents inheritances should use append or extend of _uses to avoid breaking the inheritance chain,
        instead of _uses = <whatever>
        """
        self._uses = []


class AppInfo(object):
    """
    This is a wrapper around an App's instance and the metadata of it's main module.
    """
    def __init__(self, instance, mod):
        self.__instance = instance
        self.__name = instance.__class__.__name__ if not hasattr(instance, 'NAME') else instance.NAME
        self.__author = mod.AUTHOR
        self.__pkgname = mod.PKGNAME
        self.__version = mod.VERSION
        self.__description = mod.DESCRIPTION
        self.__homepage = mod.HOMEPAGE
        self.__icon = mod.ICON
        self.__interfaces = instance._uses

    # This is a little hack to automatize the setup of properties
    def __getter(self, variable):
        def inner(self):
            return self.__dict__["_" + self.__class__.__name__ + variable]
        return inner

    def __nop(self, *args):
        pass

    # Every property can be retrieved by the __getter method but cannot be modified nor deleted
    instance = property(__getter(None, "__instance"), __nop, __nop)
    author = property(__getter(None, "__author"), __nop, __nop)
    name = property(__getter(None, "__name"), __nop, __nop)
    pkgname = property(__getter(None, "__pkgname"), __nop, __nop)
    version = property(__getter(None, "__version"), __nop, __nop)
    description = property(__getter(None, "__description"), __nop, __nop)
    homepage = property(__getter(None, "__homepage"), __nop, __nop)
    icon = property(__getter(None, "__icon"), __nop, __nop)
    interfaces = property(__getter(None, "__interfaces"), __nop, __nop)


class AppManager(Observable):
    """
    Public API for the management of apps, it's the principal way to access an app.
    This class only loads in main memory an app to became available to the entire project, to install it in the
    filesystem (and then been loaded with load_apps or load_app) we use a plugin.
    It's a singleton because the other alternative (decorate all methods with staticmethod) is impossible due to the
    need to customize the __init__ initializer.
    """
    __metaclass__ = Singleton

    def __init__(self, path_apps=None):
        super(AppManager, self).__init__()
        logger = logging.getLogger("genesis2")
        if path_apps is None:
            logger.critical("Path apps is None in AppManager.")
            stop_server()
        else:
            self.path_apps = path_apps
        # I separate the __apps (which contains AppInfo wrappers) from the instance of an App
        # (which is stored in __instance_apps) to avoid having two different AppInfos wrapping the same App
        self._apps = {}
        # In the _instance_apps is stored the unique id of the App's instance indexed by interface
        self._instance_apps = {}
        self._metadata = None

    def _unroll(self, mapping):
        """
        A useful method to unroll the _apps or _instance_apps data structures.
        """
        return list(set([x for y in mapping.values() for x in y]))

    def grab_apps(self, interface=None, flt=None):
        """
        The main method to retrieve apps that use an interface.

        Explanation:
        The core idea behind the App concept can be summed up in one fact: in the old genesis, some plugins were
        only accessed through a method in application called grab_plugins. This set of plugins is what i call Apps.
        Remember the golden rule of genesis2: an App uses services implemented by Plugins.
        So a Plugin lives in genesis2.apis and an App is registered in AppManager and is accessed through this method.
        What i have done is think about the workflow of the old genesis and improve it through a new core genesis. This
        method is one of the important ones to understand why.
        """
        if interface is None:
            # Return all the apps loaded in the system
            instance_apps = self._unroll(self._instance_apps)
            apps = self._unroll(self._apps)
            return list(filter(lambda app: id(app.instance) in instance_apps, apps))
        elif interface in self._instance_apps:
            instance_apps = self._instance_apps[interface]
            apps = filter(lambda app: id(app.instance) in instance_apps, self._unroll(self._apps))
            if isinstance(flt, FunctionType):
                apps = filter(flt, apps)
            return list(apps)
        elif len(self._instance_apps) == 0:
            return []
        else:
            logger = logging.getLogger('genesis2')
            logger.warning('Interface %s doesn\'t exists' % interface)

    # Is called by the app when it is instanced
    def register(self, instance, *interfaces):
        """
        This method is called when an app is instantiated (normally by load_app, but see the tests to understand it).
        If the instance is valid, it's recorded to been retrieved later by grab_apps.
        One of the important implementation details is that _instance_apps is used when we want to know if an app is
        already registered in genesis2. Then the instance id is translated into an AppInfo stored in _apps, which is
        retrieved to the clients or accepted by them.
        """
        instances = self._unroll(self._instance_apps)
        if isinstance(instance, App) and id(instance) not in instances and len(interfaces) > 0:
            # The _metadata is set by load_app before the App calls register
            app = AppInfo(instance, self._metadata)
            for interface in interfaces:
                if interface in self._instance_apps:
                    self._apps[interface].append(app)
                    self._instance_apps[interface].append(id(instance))
                else:
                    self._apps[interface] = [app]
                    self._instance_apps[interface] = [id(instance)]

                self.notify_observers("register", app, interface)

    def unregister(self, app, name=None):
        """
        Once an app isn't any more in the filesystem, this method erase it from the genesis environment.
        """
        if app is None:
            apps = self.grab_apps()
            if name is not None:
                for application in apps:
                    if application.name == name:
                        app = application
                        break
                if app is None:
                    return
            else:
                return
        instance_app = app.instance
        if id(instance_app) in self._unroll(self._instance_apps):
            for interface in app.interfaces:
                # The user can restrict the app to a subset of accepted interfaces
                ifaces = filter(lambda iface: iface == interface, self._instance_apps.keys())
                if len(ifaces) == 1 and id(instance_app) in self._instance_apps[ifaces[0]]:
                    self._instance_apps[ifaces[0]].remove(id(instance_app))
                    self._apps[ifaces[0]].remove(app)

                self.notify_observers("unregister", app, ifaces[0])

    def load_apps(self):
        """
        Load all apps in self.path_apps (which is set in the initializer).
        """
        apps = [app for app in os.listdir(self.path_apps) if not app.startswith('.') if not app.endswith("pyc")]
        apps = [app[:-3] if app.endswith('.py') else app for app in apps]
        apps = list(set(apps))
        apps.remove("__init__")

        self._apps = {}
        self._instance_apps = {}

        logger = logging.getLogger('genesis2')

        # The apps only depend on plugins that they use, so there cannot be a circular dependency (that's why i have
        # deleted from the old genesis).
        # The only problem is if the plugin that is used by the app isn't loaded.
        for app in apps:
            try:
                self.load_app(app)
            except AppRequirementError, e:
                logger.warning('App %s requires plugin %s, which is not available.' % (app, e.name))
            except ModuleRequirementError, e:
                logger.warning('App %s cannot be loaded due to an ImportError' % app)
                self.unregister(None, name=app)
            except BaseRequirementError, e:
                logger.warning('App %s %s' % (app, str(e)))
                self.unregister(None, name=app)
            except Exception, e:
                logger.warning('It has happened a nasty error while loading the app %s' % app)
                self.unregister(None, name=app)

        self.notify_observers("load_apps")

    def load_app(self, name_app):
        """
        Load an app stored in self.path_apps by the name name_app.

        Explanation:
        So here's one of the most important methods in the entire project. It maintains the spirit of the way the old
        genesis loads the old plugins. The important thing to note is the AppRegister() interaction and the role
        self._metadata plays later in register(); i suggest to understand them fully before blame me.
        Here's how the dance begins and ends:
           1) Someone calls load_app (probably load_apps, which is called probably by launcher)
           2) First we ensures that all the plugins are loaded (a plugin is registered in genesis2.apis by the name of
              the interface it implements except that the first letter (a I of Interface) is substituted by a P of...)
           3) Second we load all the submodules indicated in the module's data (the one that is stored in __init__.py)
           4) We instantiate all the classes that were loaded in these submodules and that inherit App
           5) When an App is instantiated it calls register(), remember that.
        """
        self._metadata = imp.load_module(name_app, *imp.find_module(name_app, [self.path_apps]))
        # The WD is the root of genesis2 project and the plugins are already loaded (see launcher) so...
        genesis2 = imp.load_module("genesis2", *imp.find_module("genesis2"))
        plugins = dir(imp.load_module("genesis2.apis", *imp.find_module("apis", genesis2.__path__)))
        for interface in self._metadata.PKGINTERFACES:
            plugin = "P" + interface[1:]
            if not plugin in plugins:
                raise AppRequirementError(plugin)

        # The party begins
        for submod in self._metadata.MODULES:
            # When the app is instantiated, its __new__ method will call register, that will use the
            # __metadata to register the plugin in __apps
            try:
                AppRegister()._classes = []
                imp.load_module(self._metadata.__name__ + "." + submod, *imp.find_module(submod, self._metadata.__path__))
                for cls in AppRegister()._classes:
                    cls()
            except ImportError, e:
                raise ModuleRequirementError(e.message.split()[-1], False)
            except Exception:
                raise
