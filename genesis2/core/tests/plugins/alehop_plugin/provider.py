from genesis2.core.core import Plugin
from genesis2.core.tests.interfaces import IAnotherInterface


class AlehopPlugin(Plugin):
    def __init__(self):
        super(AlehopPlugin, self).__init__()
        self._implements.append(IAnotherInterface)
