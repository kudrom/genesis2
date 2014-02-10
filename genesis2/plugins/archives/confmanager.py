import traceback

from genesis2.core.core import implements
from genesis2.plugins.workers.components import Component
from genesis2.core.core import Plugin
from genesis2.interfaces.resources import IConfigurable, IConfMgrHook


class ConfManager (Component):
    """
    A :class:`Component`, proxyfies access to system's config files.
    Use this when possible instead of ``open``. You'll have to create an
    :class:`IConfigurable` first, then use ``load``, ``save``, and ``commit``
    functions.
    """
    name = 'confmanager'

    configurables = {}
    hooks = []

    def load(self, id, path):
        """
        Reads a config file.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :param  path:   file location
        :type   path:   str
        :rtype:         str
        :returns:       file contents
        """
        cfg = self.get_configurable(id)
        for c in self.hooks:
            c.pre_load(cfg, path)

        with open(path, 'r') as f:
            data = f.read()

        for c in self.hooks:
            data = c.post_load(cfg, path, data)

        return data

    def save(self, id, path, data):
        """
        Writes a config file.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        """
        cfg = self.get_configurable(id)

        for c in self.hooks:
            data = c.pre_save(cfg, path, data)
            if data is None:
                return

        with open(path, 'w') as f:
            f.write(data)

        for c in self.hooks:
            c.post_save(cfg, path)

        return data

    def commit(self, id):
        """
        Notifies ConfManager that you have finished writing Configurable's files.
        For example, at this point Recovery plugin will make a backup.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        """
        cfg = self.get_configurable(id)
        for c in self.hooks:
            c.finished(cfg)

    def get_configurable(self, id):
        """
        Finds a Configurable.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :rtype:         :class:`IConfigurable`
        """
        for c in self.configurables.values():
            if c.id == id:
                return c

    def rescan(self):
        """
        Registers any newly found Configurables
        """
        self.configurables = {}
        self.hooks = []
        try:
            for cfg in self.app.grab_plugins(IConfigurable):
                self.log.debug('Registered configurable: ' + cfg.id + ' ' + str(cfg))
                self.configurables[cfg.id] = cfg
        except Exception, e:
            self.app.log.error('Configurables loading failed: ' + str(e) + traceback.format_exc())
        for h in self.app.grab_plugins(IConfMgrHook):
            self.app.log.debug('Registered configuration hook: ' + str(h))
            self.hooks.append(h)

    def on_starting(self):
        self.rescan()

    def on_stopping(self):
        pass

    def on_stopped(self):
        pass


class ConfMgrHook (Plugin):
    """
    Handy base class in case you don't want to reimplement all hook methods.
    """
    implements(IConfMgrHook)
    abstract = True

    def pre_load(self, cfg, path):
        pass

    def post_load(self, cfg, path, data):
        return data

    def pre_save(self, cfg, path, data):
        return data

    def post_save(self, cfg, path):
        pass

    def finished(self, cfg):
        pass


