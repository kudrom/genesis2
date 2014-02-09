"""
Tools for manipulating plugins and repository
"""

__all__ = [
    'BaseRequirementError',
    'PlatformRequirementError',
    'PluginRequirementError',
    'ModuleRequirementError',
    'SoftwareRequirementError',
    'PluginLoader',
    'RepositoryManager',
    'PluginInfo',
]

import os
import imp
import sys
import traceback
import weakref
import urllib2

from .exceptions import *
from .core import PluginManager
from genesis2.plugins.workers.components import ComponentManager
from genesis2.plugins.archives.confmanager import ConfManager
from genesis2.utils import BackgroundWorker, shell, shell_status, download
import genesis2

RETRY_LIMIT = 10


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


class RepositoryManager:
    """
    Manages official Genesis plugin repository. ``cfg`` is :class:`genesis.config.Config`

    - ``available`` - list(:class:`PluginInfo`), plugins available in the repository
    - ``installed`` - list(:class:`PluginInfo`), plugins that are locally installed
    - ``upgradable`` - list(:class:`PluginInfo`), plugins that are locally installed
      and have other version in the repository
    """

    def __init__(self, cfg):
        self.config = cfg
        self.server = cfg.get('genesis', 'update_server')
        self.refresh()

    def list_available(self):
        d = {}
        for x in self.available:
            d[x.id] = x
        return d

    def check_conflict(self, id, op):
        """
        Check if an operation can be performed due to dependency conflict
        """
        pdata = PluginLoader.list_plugins()
        if op == 'remove':
            for i in pdata:
                for dep in pdata[i].deps:
                    if dep[0] == 'plugin' and dep[1] == id and dep[1] in [x.id for x in self.installed]:
                        raise ImSorryDave(pdata[dep[1]].name, pdata[i].name, op)
        elif op == 'install':
            t = self.list_available()
            try:
                for i in eval(t[id].deps):
                    for dep in i[1]:
                        if dep[0] == 'plugin' and dep[1] not in [x.id for x in self.installed]:
                            raise ImSorryDave(t[id].name, t[dep[1]].name, op)
            except KeyError:
                raise Exception('There was a problem in checking dependencies. '
                                'Please try again after refreshing the plugin list. '
                                'If this problem persists, please contact Genesis maintainers.')

    def refresh(self):
        """
        Re-reads saved repository information and rebuilds installed/available lists
        """
        self.available = []
        self.installed = []
        self.update_installed()
        self.update_available()
        self.update_upgradable()

    def update_available(self):
        """
        Re-reads saved list of available plugins
        """
        try:
            data = eval(open('/var/lib/genesis/plugins.list').read())
        except:
            return
        self.available = []
        for item in data:
            inst = False
            for i in self.installed:
                if i.id == item['id'] and i.version == item['version']:
                    inst = True
                    break
            if inst:
                continue

            i = PluginInfo()
            for k, v in item.items():
                setattr(i, k, v)
            i.installed = False
            i.problem = None
            self.available.append(i)

    def update_installed(self):
        """
        Rebuilds list of installed plugins
        """
        self.installed = sorted(PluginLoader.list_plugins().values(), key=lambda x: x.name)

    def update_upgradable(self):
        """
        Rebuilds list of upgradable plugins
        """
        upg = []
        for p in self.available:
            u = False
            g = None
            for g in self.installed:
                if g.id == p.id and g.version != p.version:
                    u = True
                    break
            if u:
                g.upgradable = p.upgradable = True
                upg += [g]
        self.upgradable = upg

    def update_list(self, crit=False):
        """
        Downloads fresh list of plugins and rebuilds installed/available lists
        """
        if not os.path.exists('/var/lib/genesis'):
            os.mkdir('/var/lib/genesis')
        try:
            data = download('http://%s/genesis/list/%s' % (self.server, PluginLoader.platform), crit=crit)
        except urllib2.HTTPError, e:
            raise Exception('Application list retrieval failed with HTTP Error %s' % str(e.code))
        except urllib2.URLError, e:
            raise Exception('Application list retrieval failed - Server not found or URL malformed. '
                            'Please check your Internet settings.')
        open('/var/lib/genesis/plugins.list', 'w').write(data)
        self.update_installed()
        self.update_available()
        self.update_upgradable()

    def remove(self, id, cat=''):
        """
        Uninstalls given plugin

        :param  id:     Plugin id
        :type   id:     str
        """

        try:
            self.purge = self.config.get('genesis', 'purge')
        except:
            self.purge = '1'

        exclude = ['openssl', 'nginx']

        if cat:
            cat.put_statusmsg('Removing plugin...')
        dir = self.config.get('genesis', 'plugins')
        shell('rm -r %s/%s' % (dir, id))

        if id in PluginLoader.list_plugins():
            depends = []
            try:
                pdata = PluginLoader.list_plugins()
                thisplugin = pdata[id].deps
                for thing in thisplugin:
                    if 'app' in thing[0]:
                        depends.append((thing, 0))
                for plugin in pdata:
                    for item in enumerate(depends):
                        if item[1][0] in pdata[plugin].deps:
                            depends[item[0]] = (depends[item[0]][0], depends[item[0]][1]+1)
                for thing in depends:
                    if thing[1] <= 1 and not thing[0][1] in exclude:
                        if cat:
                            cat.put_statusmsg('Removing dependency %s...' % thing[0][1])
                        shell('systemctl stop ' + thing[0][2])
                        shell('systemctl disable ' + thing[0][2])
                        shell('pacman -%s --noconfirm ' % ('Rn' if self.purge is '1' else 'R') + thing[0][1])
            except KeyError:
                pass
            PluginLoader.unload(id)

        self.update_installed()
        self.update_available()
        if cat:
            cat.put_message('info', 'Plugin removed. Refresh page for changes to take effect.')

    def install(self, id, load=True, cat=''):
        """
        Installs a plugin

        :param  id:     Plugin id
        :type   id:     str
        :param  load:   True if you want Genesis to load the plugin immediately
        :type   load:   bool
        """
        dir = self.config.get('genesis', 'plugins')

        if cat:
            cat.put_statusmsg('Downloading plugin package...')
        download('http://%s/genesis/plugin/%s' % (self.server, id), file='%s/plugin.tar.gz' % dir, crit=True)

        self.remove(id)
        self.install_tar(load=load, cat=cat)

    def install_stream(self, stream):
        """
        Installs a plugin from a stream containing the package

        :param  stream: Data stream
        :type   stream: file
        """
        dir = self.config.get('genesis', 'plugins')
        open('%s/plugin.tar.gz' % dir, 'w').write(stream)
        self.install_tar()

    def install_tar(self, load=True, cat=''):
        """
        Unpacks and installs a ``plugin.tar.gz`` file located in the plugins directory.

        :param  load:   True if you want Genesis to load the plugin immediately
        :type   load:   bool
        """
        dir = self.config.get('genesis', 'plugins')

        if cat:
            cat.put_statusmsg('Extracting plugin package...')
        id = shell('tar tzf %s/plugin.tar.gz' % dir).split('\n')[0].strip('/')

        shell('cd %s; tar xf plugin.tar.gz' % dir)
        shell('rm %s/plugin.tar.gz' % dir)

        if load:
            PluginLoader.load(id, cat=cat)

        self.update_installed()
        self.update_available()
        self.update_upgradable()


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


class LiveInstall(BackgroundWorker):
    def run(self, rm, id, load, cat):
        rm.install(id, load=load, cat=cat)
        cat.put_message('info', 'Plugin installed. Refresh page for changes to take effect.')
        ComponentManager.get().rescan()
        ConfManager.get().rescan()
        cat._reloadfw = True
        cat.clr_statusmsg()


class LiveRemove(BackgroundWorker):
    def run(self, rm, id, cat):
        rm.remove(id, cat)
        cat._reloadfw = True
        cat.clr_statusmsg()
