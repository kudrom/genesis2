import os
import logging
from ConfigParser import SafeConfigParser
from types import FunctionType

from genesis2.utils.filesystem import create_files
from genesis2.core.core import Plugin
from exceptions import ConfFileIsInvalid, EventIsInvalid, FileIsNotRegistered
from genesis2.interfaces.resources import IConfManager, IConfParserManager, IConfGenesis2Manager
from genesis2.utils.interlocked import ClassProxy


class Configurable(object):
    def __init__(self, path, manager):
        self.manager = manager
        self.path = path

    def read(self):
        self.manager.notify_observers(self.path, 'pre_read')
        fd = open(self.path, 'r')
        self.manager.notify_observers(self.path, 'post_read')
        return fd

    def write(self, text, mode='a'):
        self.manager.notify_observers(self.path, 'pre_write')
        fd = open(self.path, mode)
        self.manager.notify_observers(self.path, 'post_write')
        return fd.write(text)


class ConfManager(Plugin):
    def __init__(self):
        super(ConfManager, self).__init__()
        self._implements.append(IConfManager)
        self._conf_class = Configurable
        self._configurables = {}
        self._callbacks = {'pre_read': [], 'post_read': [], 'pre_write': [], 'post_write': []}

    def _create_conf(self, path, *args, **kwargs):
        if path not in self._configurables:
            if os.path.exists(path) and os.path.isfile(path) and path.startswith('/'):
                conf = ClassProxy(self._conf_class(path, self, *args, **kwargs))
                self._configurables[path] = conf
                return conf
            else:
                raise ConfFileIsInvalid(path)
        return self._configurables[path]

    def get_conf(self, path):
        return self._create_conf(path)

    # Me falta el path, probablemente haya que cambiar la estructura de _callbacks a {path: {event: [observables]}}
    def add_observer(self, observer, path):
        namespace = dir(observer)
        for event in self._callbacks:
            if event in namespace and isinstance(observer.event, FunctionType):
                self._callbacks[event].append(observer)

    def delete_observer(self, observer):
        for event, observers in self._callbacks.values():
            if observer in observers:
                self._callbacks[event].remove(observer)

    def notify_observers(self, path, event):
        logger = logging.getLogger('genesis2')
        if event in self._callbacks:
            if path in self._configurables:
                for observer in self._callbacks[event]:
                    callback = getattr(observer, event)
                    try:
                        callback(path)
                    except:
                        logger.warning('Observer %s[%s] failed while performing %s on %s.' %
                                       (observer, observer.__module__, event, path))
            else:
                raise FileIsNotRegistered(path)
        else:
            raise EventIsInvalid(event)


class ParserConfigurable(SafeConfigParser):
    def __init__(self, path, manager):
        super(ParserConfigurable, self).__init__()
        self.manager = manager
        self.path = path

    def read(self):
        self.manager.notify_observers(self.path, 'pre_read')
        super(ParserConfigurable, self).read(self.path)
        self.manager.notify_observers(self.path, 'post_read')

    def write(self, mode='a'):
        fp = open(self.path, mode)
        self.manager.notify_observers(self.path, 'pre_write')
        super(ParserConfigurable, self).write(fp)
        self.manager.notify_observers(self.path, 'post_write')


class ConfParserManager(ConfManager):
    def __init__(self):
        super(ConfParserManager, self).__init__()
        self._implements = [IConfParserManager]
        self._conf_class = ParserConfigurable


class Genesis2Configurable(ParserConfigurable):
    def __init__(self, path, manager):
        ParserConfigurable.__init__(self, path, manager)

    def get_plug_option(self, plugin, option):
        section = 'cfg_' + plugin
        self.get(section, option)

    def set_plug_option(self, plugin, option, value):
        section = 'cfg_' + plugin
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, option, value)

    def remove_plug_option(self, plugin, option):
        section = 'cfg_' + plugin
        if self.has_section(section) and self.has_option(section, option):
            self.remove_option(section, option)

    def get_plug(self, plugin):
        section = 'cfg_' + plugin
        if not self.has_section(section):
            return self.options(section)

    def delete_plug(self, plugin):
        section = 'cfg_' + plugin
        if self.has_section(section):
            self.remove_section(section)


class Genesis2Proxy(object):
    def __init__(self, path, manager):
        self.path = path
        self.manager = manager
        self.users_dir = os.path.join(os.path.dirname(self.path), 'users')

        if not os.path.exists(self.users_dir) or not os.path.isdir(self.users_dir):
            os.mkdir(self.users_dir)

    def add_user(self, user):
        path_user = os.path.join(self.users_dir, user)
        if not os.path.exists(path_user) or not os.path.isfile(path_user):
            open(path_user, 'w').close()


class Genesis2ConfManager(ConfManager):
    def __init__(self):
        super(Genesis2ConfManager, self).__init__()
        self._implements = [IConfGenesis2Manager]
        self._conf_class = Genesis2Configurable
