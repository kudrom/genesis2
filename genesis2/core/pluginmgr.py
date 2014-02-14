"""
Tools for manipulating plugins and repository
"""

import os
import imp
import sys
import traceback
import weakref

from genesis2.core.exceptions import PlatformRequirementError, ModuleRequirementError, GenesisVersionRequirementError, \
    BaseRequirementError, PluginRequirementError, SoftwareRequirementError, CrashedError
from genesis2.utils import shell, shell_status, PrioList
import genesis2

RETRY_LIMIT = 10


class PluginInfo:
    """
    Container for the plugin description
    - ``upgradable`` - `bool`, if the plugin can be upgraded
    - ``problem``- :class:`Exception` which occured while loading plugin, else ``None``
    - ``deps`` - list of dependency tuples
    And other fields read by :class:`PluginLoader` from plugin's ``__init__.py``
    """

    def __init__(self):
        self.upgradable = False
        self.problem = None
        self.deps = []

    def str_req(self):
        """
        Formats plugin's unmet requirements into human-readable string

        :returns:    str
        """

        reqs = []
        for p in self.deps:
            if any(x in [PluginLoader.platform, 'any'] for x in p[0]):
                for r in p[1]:
                    try:
                        PluginLoader.verify_dep(r)
                    except Exception, e:
                        reqs.append(str(e))
        return ', '.join(reqs)


class PluginLoader:
    """
    Handles plugin loading and unloading
    """

    __classes = {}
    __plugins = {}
    __submods = {}
    __managers = []
    __observers = []
    platform = None
    log = None
    path = None

    @staticmethod
    def initialize(log, path, platform):
        """
        Initializes the PluginLoader

        :param  log:        Logger
        :type   log:        :class:`logging.Logger`
        :param  path:       Path to the plugins
        :type   path:       str
        :param  platform:   System platform for plugin validation
        :type   platform:   str
        """

        PluginLoader.log = log
        PluginLoader.path = path
        PluginLoader.platform = platform

    @staticmethod
    def list_plugins():
        """
        Returns dict of :class:`PluginInfo` for all plugins
        """

        return PluginLoader.__plugins

    @staticmethod
    def register_mgr(mgr):
        """
        Registers an :class:`genesis.com.PluginManager` from which the unloaded
        classes will be removed when a plugin is unloaded
        """
        PluginLoader.__managers.append(mgr)

    @staticmethod
    def register_observer(mgr):
        """
        Registers an observer which will be notified when plugin set is changed.
        Observer should have a callable ``plugins_changed`` method.
        """
        PluginLoader.__observers.append(weakref.ref(mgr, callback=PluginLoader.__unregister_observer))

    @staticmethod
    def __unregister_observer(ref):
        PluginLoader.__observers.remove(ref)

    @staticmethod
    def notify_plugins_changed():
        """
        Notifies all observers that plugin set has changed.
        """
        for o in PluginLoader.__observers:
            if o():
                o().plugins_changed()

    @staticmethod
    def load(plugin, cat=''):
        """
        Loads given plugin
        """
        log = PluginLoader.log
        path = PluginLoader.path
        platform = PluginLoader.platform
        from genesis2 import generation

        if cat:
            cat.put_statusmsg('Loading plugin %s...' % plugin)
        log.debug('Loading plugin %s' % plugin)
        try:
            mod = imp.load_module(plugin, *imp.find_module(plugin, [path]))
            log.debug('  -- version ' + mod.VERSION)
        except:
            log.warn(' *** Plugin not loadable: ' + plugin)
            return

        info = PluginInfo()
        try:
            # Save info
            info.id = plugin
            info.iconfont = mod.ICON
            info.name, info.desc, info.version = mod.NAME, mod.DESCRIPTION, mod.VERSION
            info.author, info.homepage = mod.AUTHOR, mod.HOMEPAGE
            info.deps = []
            info.problem = None
            info.installed = True
            info.descriptor = mod

            PluginLoader.__plugins[plugin] = info

            # Verify platform
            if mod.PLATFORMS != ['any'] and not platform in mod.PLATFORMS:
                raise PlatformRequirementError(mod.PLATFORMS)

            # Verify version
            if not 'GENERATION' in mod.__dict__ or mod.GENERATION != generation:
                raise GenesisVersionRequirementError('other Genesis platform generation')

            # Verify dependencies
            if hasattr(mod, 'DEPS'):
                deps = []
                for k in mod.DEPS:
                    if platform.lower() in k[0] or 'any' in k[0]:
                        deps = k[1]
                        break
                info.deps = deps
                for req in deps:
                    PluginLoader.verify_dep(req, cat)

            PluginLoader.__classes[plugin] = []
            PluginLoader.__submods[plugin] = {}

            # Load submodules
            for submod in mod.MODULES:
                try:
                    log.debug('  -> %s' % submod)
                    PluginManager.start_tracking()
                    m = imp.load_module(plugin + '.' + submod, *imp.find_module(submod, mod.__path__))
                    classes = PluginManager.stop_tracking()
                    # Record new Plugin subclasses
                    PluginLoader.__classes[plugin] += classes
                    # Store submodule
                    PluginLoader.__submods[plugin][submod] = m
                    setattr(mod, submod, m)
                except ImportError, e:
                    del mod
                    raise ModuleRequirementError(e.message.split()[-1], False)
                except Exception:
                    del mod
                    raise

            # Store the whole plugin
            setattr(genesis2.plugins, plugin, mod)
            PluginLoader.notify_plugins_changed()
        except BaseRequirementError, e:
            info.problem = e
            raise e
        except Exception, e:
            log.warn(' *** Plugin loading failed: %s' % str(e))
            print traceback.format_exc()
            PluginLoader.unload(plugin)
            info.problem = CrashedError(e)

    @staticmethod
    def load_plugins():
        """
        Loads all plugins from plugin path
        """
        log = PluginLoader.log
        path = PluginLoader.path

        plugs = [plug for plug in os.listdir(path) if not plug.startswith('.')]
        plugs = [plug[:-3] if plug.endswith('.py') else plug for plug in plugs]
        plugs = list(set(plugs))

        queue = plugs
        retries = {}

        while len(queue) > 0:
            plugin = queue[-1]
            if not plugin in retries:
                retries[plugin] = 0

            try:
                PluginLoader.load(plugin)
                queue.remove(plugin)
            except PluginRequirementError, e:
                retries[plugin] += 1
                if retries[plugin] > RETRY_LIMIT:
                    log.error('Circular dependency between %s and %s. Aborting' % (plugin, e.name))
                    sys.exit(1)
                try:
                    queue.remove(e.name)
                    queue.append(e.name)
                    if (e.name in PluginLoader.__plugins) and (PluginLoader.__plugins[e.name].problem is not None):
                        raise e
                except:
                    log.warn('Plugin %s requires plugin %s, which is not available.' % (plugin, e.name))
                    queue.remove(plugin)
            except BaseRequirementError, e:
                log.warn('Plugin %s %s' % (plugin, str(e)))
                PluginLoader.unload(plugin)
                queue.remove(plugin)
            except Exception:
                PluginLoader.unload(plugin)
                queue.remove(plugin)
        log.info('Plugins loaded.')

    @staticmethod
    def unload(plugin):
        """
        Unloads given plugin
        """
        PluginLoader.log.info('Unloading plugin %s' % plugin)
        if plugin in PluginLoader.__classes:
            for cls in PluginLoader.__classes[plugin]:
                for m in PluginLoader.__managers:
                    i = m.instance_get(cls)
                    if i is not None:
                        i.unload()
                PluginManager.class_unregister(cls)
        if plugin in PluginLoader.__plugins:
            del PluginLoader.__plugins[plugin]
        if plugin in PluginLoader.__submods:
            del PluginLoader.__submods[plugin]
        if plugin in PluginLoader.__classes:
            del PluginLoader.__classes[plugin]
        PluginLoader.notify_plugins_changed()

    @staticmethod
    def verify_dep(dep, cat=''):
        """
        Verifies that given plugin dependency is satisfied. Returns bool
        """
        platform = PluginLoader.platform

        if dep[0] == 'app':
            if shell_status('which '+dep[2]) != 0 and shell_status('pacman -Q '+dep[1]) != 0:
                if platform == 'arch' or platform == 'arkos':
                    try:
                        if cat:
                            cat.put_statusmsg('Installing dependency %s...' % dep[1])
                        shell('pacman -Sy --noconfirm --needed '+dep[1])
                        shell('systemctl enable '+dep[2])
                    except:
                        raise SoftwareRequirementError(*dep[1:])
                elif platform == 'debian':
                    try:
                        shell('apt-get -y --force-yes install '+dep[2])
                    except:
                        raise SoftwareRequirementError(*dep[1:])
                elif platform == 'gentoo':
                    try:
                        shell('emerge '+dep[2])
                    except:
                        raise SoftwareRequirementError(*dep[1:])
                elif platform == 'freebsd':
                    try:
                        shell('portupgrade -R '+dep[2])
                    except:
                        raise SoftwareRequirementError(*dep[1:])
                elif platform == 'centos' or platform == 'fedora':
                    try:
                        shell('yum -y install  '+dep[2])
                    except:
                        raise SoftwareRequirementError(*dep[1:])
                else:
                    raise SoftwareRequirementError(*dep[1:])
        if dep[0] == 'plugin':
            if not dep[1] in PluginLoader.list_plugins() or \
                    PluginLoader.__plugins[dep[1]].problem:
                raise PluginRequirementError(*dep[1:])
        if dep[0] == 'module':
            try:
                exec('import %s' % dep[1])
            except:
                # Let's try to install it anyway
                shell('pip2 install %s' % dep[2])
                raise ModuleRequirementError(*dep[1:])

    @staticmethod
    def get_plugin_path(app, id):
        """
        Returns path for plugin's files. Parameters: :class:`genesis.middleware.Application`, ``str``
        """
        if id in PluginLoader.list_plugins():
            return app.config.get('genesis', 'plugins')
        else:
            # ./plugins
            return os.path.join(os.path.split(__file__)[0], 'plugins')


class PluginManager (object):
    """ Holds all registered classes, instances and implementations
    You should have one class instantiated from both PluginManager and Plugin
    to trigger plugins magick
    """
    # Class-wide properties
    __classes = []
    __plugins = {}
    __tracking = False
    __tracker = None

    def __init__(self):
        self.__instances = {}

    @staticmethod
    def class_register(cls):
        """
        Registers a new class

        :param  cls:    class
        :type   cls:    type
        """
        PluginManager.__classes.append(cls)
        if PluginManager.__tracking:
            PluginManager.__tracker.append(cls)

    @staticmethod
    def class_unregister(cls):
        """
        Unregisters a class

        :param  cls:    class
        :type   cls:    type
        """
        PluginManager.__classes.remove(cls)
        for lst in PluginManager.__plugins.values():
            if cls in lst:
                lst.remove(cls)

    @staticmethod
    def class_list():
        """
        Lists all registered classes

        :returns:       list(:class:`type`)
        """
        return PluginManager.__classes

    @staticmethod
    def plugin_list():
        return PluginManager.__plugins

    @staticmethod
    def plugin_register(iface, cls):
        """
        Registers a :class:`Plugin` for implementing an :class:`Interface`

        :param  iface:  interface
        :type   iface:  type
        :param  cls:    plugin
        :type   cls:    :class:`Plugin`
        """
        lst = PluginManager.__plugins.setdefault(iface, PrioList())
        for item in lst:
            if str(item) == str(cls):
                return
        lst.append(cls)

    @staticmethod
    def plugin_get(iface):
        """
        Returns plugins that implement given :class:`Interface`

        :param  iface:  interface
        :type   iface:  type
        """
        return PluginManager.__plugins.get(iface, [])

    @staticmethod
    def start_tracking():
        """
        Starts internal registration tracker
        """
        PluginManager.__tracking = True
        PluginManager.__tracker = []

    @staticmethod
    def stop_tracking():
        """
        Stops internal registration tracker and returns all classes
        registered since calling ``start_tracking``
        """
        PluginManager.__tracking = False
        return PluginManager.__tracker

    def instance_get(self, cls, instantiate=False):
        """
        Gets a saved instance for the :class:`Plugin` subclass

        :param  instantiate:  instantiate plugin if it wasn't instantiate before
        :type   instantiate:  bool
        """
        if not self.plugin_enabled(cls):
            return None
        inst = self.__instances.get(cls)
        if instantiate and inst is None:
            if cls not in PluginManager.__classes:
                raise Exception('Class "%s" is not registered' % cls.__name__)
            try:
                inst = cls(self)
            except TypeError, e:
                print traceback.format_exc()
                raise Exception('Unable instantiate plugin %r (%s)' % (cls, e))

        return inst

    def instance_set(self, cls, inst):
        self.__instances[cls] = inst

    def instance_list(self):
        return self.__instances

    def plugin_enabled(self, cls):
        """
        Called to check if :class:`Plugin` is eligible for running on this system

        :returns: bool
        """
        return True

    def plugin_activated(self, plugin):
        """
        Called when a :class:`Plugin` is successfully instantiated
        """
