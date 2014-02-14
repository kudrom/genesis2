from genesis2.core.core import App
from genesis2.core.tests.test_app import IFakeInterface


class MyAwesomeApp(App):
    def __init__(self):
        super(MyAwesomeApp, self).__init__()
        self._uses.append(IFakeInterface)

    def required(self):
        print "This is awesome"