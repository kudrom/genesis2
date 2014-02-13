import imp
import os
from types import FunctionType

from exceptions import AppRequirementError, BaseRequirementError, ModuleRequirementError
from core import Observable, GenesisManager, App, Singleton


class AppInfo(object):
    __dir = {}

    def __init__(self, instance, mod):
        self.__instance = instance
        self.__author = mod.AUTHOR
        self.__name = mod.NAME
        self.__description = mod.DESCRIPTION
        self.__homepage = mod.HOMEPAGE
        self.__icon = mod.ICON
        self.__interfaces = mod.INTERFACES
        # A little hack to automatize the property creation
        for item in dir(self):
            starter = "_" + self.__class__.__name__ + "__"
            # We filter out the "public" attributes
            if item.startswith(starter):
                AppInfo._AppInfo__dir[item.replace(starter, "")] = getattr(self, item)

    # This is the continuation of the hack
    def __getter(self, variable):
        def inner(self):
            return AppInfo._AppInfo__dir[variable]
        return inner

    def __nop(self, *args):
        pass

    # Every property can be retrieved by the __getter method but cannot be modified nor deleted
    instance = property(__getter(None, "instance"), __nop, __nop)
    author = property(__getter(None, "author"), __nop, __nop)
    name = property(__getter(None, "name"), __nop, __nop)
    description = property(__getter(None, "description"), __nop, __nop)
    homepage = property(__getter(None, "homepage"), __nop, __nop)
    icon = property(__getter(None, "icon"), __nop, __nop)
    interfaces = property(__getter(None, "interfaces"), __nop, __nop)


class AppManager(Observable):
    """
    Public API for the management of apps.
    This class only loads in main memory an app to became available to the entire project,
    to install it in the filesystem we use a plugin.
    It also provides the access to all apps loaded in the system.
    I cannot decorate register or load_apps or load_app with the staticmethod so this manager has to be a Singleton.
    """
    __metaclass__ = Singleton

    def __init__(self, path_apps=None):
        super(AppManager, self).__init__()
        if path_apps is None:
            # No se puede implementar con un Configurable? (GenesisManager)
            self.path_apps = GenesisManager().get_config().get("genesis", "apps_path")
        else:
            self.path_apps = path_apps
        # I separate the AppInfo(__apps) from the instance of an App (__instance_apps)  to avoid having
        # two different AppInfos wrapping the same App (with the same AppInfo._instance)
        self.__apps = {}
        self.__instance_apps = {}
        self.load_apps()

    def grab_apps(self, interface=None, flt=None):
        if interface is None:
            # Return all the apps loaded in the system
            instance_apps = list(set([x for y in self.__instance_apps.values() for x in y]))
            return list(map(lambda app: self.__apps[id(app)], instance_apps))
        elif interface in self.__instance_apps:
            instance_apps = self.__instance_apps[interface]
            apps = map(lambda app: self.__apps[id(app)], instance_apps)
            if isinstance(flt, FunctionType):
                apps = filter(flt, apps)
            return list(apps)
        else:
            # (kudrom) TODO: log it
            return

    # Is called by the app when it is instanced
    def register(self, instance, *interfaces):
        app = AppInfo(instance, self.__metadata)
        if isinstance(app, App) and app not in self.grab_apps() and len(interfaces) > 0:
            for interface in interfaces:
                if interface in self.__apps:
                    self.__apps[interface].append(app)
                else:
                    self.__apps[interface] = [app]

    def unregister(self, app):
        if app in self.grab_apps():
            # The app can only use a set of interfaces that must be defined in her metadata
            # so it cannot access any other interfaces and therefore
            instance_app = app.instance()
            for interface in app.interfaces():
                # The user can restrict the app to a subset of accepted interfaces
                if instance_app in self.__apps[interface]:
                    del self.__instance_apps[id(app)]
                    del self.__apps[interface][app]

    def load_apps(self):
        apps = [app for app in os.listdir(self.path_apps) if not app.startswith('.')]
        apps = [app[:-3] if app.endswith('.py') else app for app in apps]
        apps = list(set(apps))

        # (kudrom) TODO: I have to log it
        # The apps only depend on plugins that they use, so there cannot be a circular dependency.
        # The only problem is if the plugin isn't loaded.
        for app in apps:
            try:
                self.load_app(app)
            except AppRequirementError, e:
                #log.warn('App %s requires plugin %s, which is not available.' % (app, e.name))
                pass
            except BaseRequirementError, e:
                #log.warn('App %s %s' % (app, str(e)))
                self.unregister(app)
            except Exception:
                self.unregister(app)
        #log.info('Plugins loaded.')

    def load_app(self, name_app):
        self.__metadata = imp.load_module(name_app, *imp.find_module(name_app, self.path_apps))
        # The WD is the root of genesis2 project and the plugins are already loaded so...
        plugins = imp.load_module("apis", *imp.find_module("apis", "./genesis2"))
        for interface in self.__metadata.INTERFACES:
            plugin = interface[0] = "P"
            if not plugin in plugins:
                raise AppRequirementError(plugin)

        # The party begins
        for submod in self.__metadata.MODULES:
            # When the app is instantiated, its __new__ method will call register, that will use the
            # __metadata to register the plugin in __apps
            try:
                imp.load_module(plugin + "." + submod, *imp.find_module(submod, self.__metadata.__path__))
            except ImportError, e:
                raise ModuleRequirementError(e.message.split()[-1], False)
            except Exception:
                raise
