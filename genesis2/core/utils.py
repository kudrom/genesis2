import weakref


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
    """
    Class to add the observer design pattern.
    """
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
    a control of the accesses by all the Apps in the system, each resource is wrapped by a plugin that controls it. An
    interface is only implemented by a unique plugin and establish the set of methods that it must define, it also
    serves to deny or allow access from an App to a Plugin (only if the app declares that it uses the interface, the
    plugin that implements it will allow the accesses).
    A plugin can implement various interfaces at the same time.
    Interface inheritance is allowed but the base classes must be declared as abstract to forbid the implementation of
    them by a Plugin. Interface inheritance is a really awesome way to model the services provided by the arkos
    platform. More on this topic in the documentation.
    Advantages:
        - The platform problem (allow genesis to be installed in Arch, Debian or you name it) is solved, you simply
          need to build a different set of plugins and all the Apps and all of the genesis core would work as usual.
        - The floor of access control to the untrusted code of the Apps is established, allowing a dynamic growth of
          the Apps community because we are allowing developers to build, test and deploy their own App without the
          pain to being monitored by the arkOS team (to ensure the the app isn't malware).
        - Basically the system is decoupled and both flexibility and scalability could be approached.

    The app_requirements field enforce every App that uses the interface to implement a set of methods, this is used to
    grant to the clients of the App that the App implements a set of methods (read CategoryPlugin to see an example).
    """

    def __init__(self):
        self._app_requirements = []
