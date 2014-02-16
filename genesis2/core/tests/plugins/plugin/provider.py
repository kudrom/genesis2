from genesis2.core.core import Plugin
from genesis2.core.tests.interfaces import IFakeInterface


class MyAwesomePlugin(Plugin):
    def __init__(self):
        super(MyAwesomePlugin, self).__init__()
        self._implements.append(IFakeInterface)

    def non_required(self):
        return "fucking awesome"
