from genesis2.core.core import App
from genesis2.core.tests.interfaces import IFakeInterface, IAnotherInterface
from genesis2.apis import PFakeInterface, PAnotherInterface


class IntegrationApp(App):
    def __init__(self):
        super(IntegrationApp, self).__init__()
        self._uses.append(IFakeInterface)

    def required(self):
        ret = PFakeInterface.non_required()
        return ret + ": I agree"


class ControlAccessApp(App):
    def __init__(self):
        super(ControlAccessApp, self).__init__()
        self._uses.append(IAnotherInterface)

    def required(self):
        ret = PFakeInterface.non_required()
        return ret + ": I agree"


