

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
