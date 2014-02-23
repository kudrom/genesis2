import weakref


class Singleton(type):
    """
    From https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    I prefer to use Singleton classes instead of @staticmethod because in this way i can use the __init__ method and
    customize the class with the ability of the self. Plus, sometimes it's impossible to use static methods, see
    some core Plugins to understand why.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Observable(object):
    """
    Class to add the observer design pattern to anyone that inherits from this class.
    """
    def __init__(self):
        self.__observers = []

    def get_n_observers(self):
        return len(self.__observers)

    def add_observer(self, observer):
        # Duck typing
        if hasattr(observer, "notify"):
            ref = weakref.ref(observer, self.remove_observer)
            self.__observers.append(ref)
            return ref

    def remove_observer(self, observer):
        if observer in self.__observers:
            self.__observers.remove(observer)

    def notify_observers(self, msg, *args):
        for observer in self.__observers:
            observer().notify(self, msg, *args)


class GenesisManager():
    """
    Here's where some hot genesis objects should be referenced to allow that anyone could use them.
    One clear example is the ParserConfig of genesis2.conf.
    """
    __metaclass__ = Singleton

    def __init__(self, config):
        super(GenesisManager, self).__init__()
        self.__config = config

    @property
    def config(self):
        return self.__config

    @config.deleter
    def config(self):
        pass

    @config.setter
    def config(self):
        pass


class Interface(object):
    """
    Base abstract class for all interfaces.
    An interface is:
        - An abstraction to wrap the access to a system's resource (only one) with a defined set of methods.
        - Part of the mechanism that is used to retrieve a set of apps that use a defined interface (see AppManager).
        - The specification/guide to build up the real wrapper around a set of resources via a Plugin.
        - One of the most important concepts in genesis2.

    Explication:
    An App will use a set of resources of the system to provide a defined functionality to the final user, to enforce
    a control of the accesses by all the Apps in the system, each resource is wrapped by a plugin that controls it.
    Each Plugin in the system follows a set of Interfaces that describes the set of methods that will manage the
    wrapped resource. An interface is only implemented by a unique plugin and it establishes the set of methods that
    both the plugin and the app must define to _use/_implement the Interface (an interface therefore is kind of the
    specification  of an API).
    The reason behind the enforcement that compel an App to define the methods that the Interface define in
    _app_requirements can be summed up in one fact: sometimes someone (normally an App) wants to know the apps that
    are using some interface, and most of the time these clients also want some common behaviour in these set of Apps,
    that's why in the old genesis the now-called-Apps (a weird-practical-subset of the old Plugins) inherited a Plugin:
    because we need to assure that an App implements some methods *always* to establish a common behaviour that is
    needed by some clients (see CategoryPlugin to understand it better).
    The reason behind the enforcement that compel a Plugin to define some subset of the methods in a Interface (all the
    methods minus those in _app_requirements) is due to the fact that a Plugin is the implementation of the Interface.
    An interface also is used to deny or allow access from an App to a Plugin (only if the app declares that
    it  _uses the interface, the plugin that _implements it will allow the accesses).
    A plugin can implement various interfaces at the same time, there's no reason to coerce it.
    Interface inheritance is allowed but the base classes must be declared as abstract to forbid the implementation of
    them by a Plugin. Interface inheritance is a really awesome way to model the services provided by the arkos
    platform. More on this topic in the documentation.

    Advantages of the new Interfaces:
        - The platform problem (allow genesis to be installed in Arch, Debian or you name it) is solved, you simply
          need to build a different set of plugins and all the Apps and all of the genesis core would work as usual.
        - The floor of access control to the untrusted code of the Apps is established, allowing a dynamic growth of
          the Apps community because we are allowing developers to build, test and deploy their own App without the
          pain to being monitored by the arkOS team (to ensure the the app isn't doing what it should be doing).
        - Basically the system is decoupled and therefore it's flexible and scalable.
    """

    def __init__(self):
        self._app_requirements = []
