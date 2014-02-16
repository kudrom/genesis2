from genesis2.core.utils import Interface


class IAnotherInterface(Interface):
    def __init__(self):
        super(IAnotherInterface, self).__init__()


class IFakeInterface(Interface):
    def __init__(self):
        super(IFakeInterface, self).__init__()
        self._app_requirements.append(self.required.__name__)

    def required(self):
        pass

    def non_required(self):
        pass
