from genesis2.core.utils import Interface


class IConfManager(Interface):
    def __init__(self):
        super(IConfManager, self).__init__()

    def get_conf(self, path):
        pass

    def add_observer(self, path):
        pass

    def delete_observer(self, path):
        pass

    def notify_observers(self, path, event):
        pass


class IConfParserManager(IConfManager):
    def __init__(self):
        super(IConfParserManager, self).__init__()


class IConfGenesis2Manager(IConfParserManager):
    def __init__(self):
        super(IConfGenesis2Manager, self).__init__()


class IComponent (Interface):
    """
    Base interface for background components.

    See :class:`Component`.
    """
    def run(self):
        pass

