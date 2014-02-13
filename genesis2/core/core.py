import inspect
import weakref

from pluginmgr import PluginManager
from appmgr import AppManager
from exceptions import AppInterfaceImplError


class Singleton(type):
    """
    From https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    I prefer to use Singleton classes instead of @staticmethod because in this way i
    can use the __init__ method and initialize the fields there instead that in the
    body of the class definition.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Observable(object):
    def __init__(self):
        self.__observers = []

    def add_observer(self, observer):
        # Duck typing
        if hasattr(observer, "notify"):
            self.__observers.append(weakref.ref(observer, callback=self.remove_observer))

    def remove_observer(self, observer):
        if observer in self.__observers:
            del self.__observers[observer]

    def notify_observers(self):
        for observer in self.__observers:
            observer.notify()


# (kudrom) TODO: Initialize it in launcher
class GenesisManager():
    __metaclass__ = Singleton

    def __init__(self, config):
        super(GenesisManager, self).__init__()
        self.__config = config

    def get_config(self):
        return self.__config


def implements(*interfaces):
    """
    Used to note that a :class:`Plugin` implements an :class:`Interface`.
    Example:

        class IFoo (Interface):
            pass

        class IBaz (Interface):
            pass

        class FooBazImp (Plugin):
            implements (IFoo, IBaz)
    """

    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    frame_locals = frame.f_locals

    if ((frame_locals is frame.f_globals) or
            ('__module__' not in frame_locals)):
        raise TypeError('implements() can only be used in class definition')

    if '_implements' in frame_locals:
        raise TypeError('implements() could be used only once')

    frame_locals.setdefault('_implements', []).extend(interfaces)
    # TODO: trac also all base interfaces (if needed)


class Interface(object):
    """ Base abstract class for all interfaces

    Can be used as callable (decorator)
    to check if Plugin implements all methods
    (internal use only)
    """

    def __init__(self):
        self._app_requirements = []

    def __call__(self, cls):
        # Check that target class supports all our interface methods
        cls_methods = [m for m in dir(cls) if not m.startswith('_')]

        # Check local interface methods
        methods = [m for m in dir(self.__class__) if not m.startswith('_')]
        # Filter out property methods
        methods = [m for m in methods if m not in dir(property)]

        for method in methods:
            if method not in cls_methods:
                raise AttributeError(
                    "%s implementing interface %s, does not have '%s' method" %
                    (cls, self.__class__, method))


class MetaPlugin (type):
    """
    Metaclass for Plugin
    """

    def __new__(cls, name, bases, d):
        """ Create new class """

        # Create new class
        new_class = type.__new__(cls, name, bases, d)

        # If we creating base class, do nothing
        if name == 'Plugin':
            return new_class

        # Override __init__ for Plugins, for instantiation process
        if True not in [issubclass(x, PluginManager) for x in bases]:
            # Allow Plugins to have own __init__ without parameters
            init = d.get('__init__')
            if not init:
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for init in [b.__init__._original for b in new_class.mro()
                             if issubclass(b, Plugin)
                             and '__init__' in b.__dict__]:
                    break

            def maybe_init(self, plugin_manager, init=init, cls=new_class):
                if plugin_manager.instance_get(cls) is None:
                    # Plugin is just created
                    if init:
                        init(self)
                    if not self.multi_instance:
                        plugin_manager.instance_set(cls, self)
            maybe_init._original = init
            new_class.__init__ = maybe_init

        # If this is abstract class, do no record it
        if d.get('abstract'):
            return new_class

        # Save created class for future reference
        PluginManager.class_register(new_class)

        # Collect all interfaces that this class implements
        interfaces = d.get('_implements', [])
        for base in [base for base in new_class.mro()[1:] if hasattr(base, '_implements')]:
            interfaces.extend(base._implements)

        # Delete duplicates, in case we inherit same Intarfaces
        # or we need to override priority
        _ints = []
        _interfaces = []
        for interface in interfaces:
            _int = interface
            if isinstance(interface, tuple):
                _int = interface[0]

            if _int not in _ints:
                _ints.append(_int)
                _interfaces.append(interface)

        interfaces = _interfaces

        # Check that class supports all needed methods
        for interface in interfaces:
            _int = interface
            if isinstance(interface, tuple):
                _int = interface[0]
            _int()(new_class)

        # Register plugin
        for interface in interfaces:
            if isinstance(interface, tuple):
                PluginManager.plugin_register(interface[0], (new_class, interface[1]))
            else:
                PluginManager.plugin_register(interface, new_class)

        return new_class


class Plugin (object):
    """
    Base class for all plugins

    - ``multi_instance`` - `bool`, if True, plugin will be not treated as a singleton
    - ``abstract`` - `bool`, abstract plugins are not registered in :class:`PluginManager`
    - ``platform`` - `list(str)`, platforms where the Plugin can be run
    - ``plugin_id`` - `str`, autoset to lowercase class name
    """

    __metaclass__ = MetaPlugin

    multi_instance = False

    platform = ['any']

    def __init__(self):
        self._implements = []

    def __new__(cls, *args, **kwargs):
        """ Returns a class instance,
        If it already instantiated, return it
        otherwise return new instance
        """
        if issubclass(cls, PluginManager):
            # If we also a PluginManager, just create and return
            self = super(Plugin, cls).__new__(cls)
            self.plugin_manager = self
            return self

        # Normal case when we are standalone plugin
        self = None
        plugin_manager = args[0]
        if not cls.multi_instance:
            self = plugin_manager.instance_get(cls)

        if self is None:
            self = super(Plugin, cls).__new__(cls)
            self.plugin_manager = plugin_manager
            self.plugin_id = cls.__name__.lower()
            # Allow PluginManager implementation to update Plugin
            plugin_manager.plugin_activated(self)

        return self

    def unload(self):
        """
        Called when plugin class is being unloaded by
        :class:`genesis.plugmgr.PluginLoader`
        """


class App(object):
    __metaclass__ = MetaApp

    def __init__(self):
        self._uses = []


class MetaApp(Singleton):
    def __call__(cls, *args, **kwargs):
        instance = super(MetaApp, cls).__call__(*args, **kwargs)
        methods = dir(instance)
        for interface in instance._uses:
            requirements = interface()._app_requirements
            for requirement in requirements:
                if requirement not in methods:
                    raise AppInterfaceImplError
        AppManager().register(instance, *instance._uses)
