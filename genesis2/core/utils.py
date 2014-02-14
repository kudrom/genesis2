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
