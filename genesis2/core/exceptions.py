class BaseRequirementError(Exception):
    """
    Basic exception that means an app/plugin wasn't loaded due to some violation
    """


class PlatformRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to unsupported platform
    """

    def __init__(self, lst):
        super(PlatformRequirementError, self).__init__()
        self.lst = lst

    def __str__(self):
        return 'requires platforms %s' % self.lst


class GenesisVersionRequirementError(BaseRequirementError):
    """
    Exception that means an app/plugin wasn't loaded due to unsupported Genesis version
    """

    def __init__(self, lst):
        super(GenesisVersionRequirementError, self).__init__()
        self.lst = lst

    def __str__(self):
        return 'requires %s' % self.lst


class PluginInterfaceImplError(BaseRequirementError):
    """
    Exception that means a plugin doesn't implement a method that should implement by the definition of the Interface
    """
    def __init__(self, plugin, interface, method):
        super(PluginInterfaceImplError, self).__init__()
        self.plugin = plugin
        self.interface = interface
        self.method = method

    def __str__(self):
        return ("%s can't be loaded because it doesn't implements the %s method that"
                " the %s interface requires." % (self.plugin, self.method, self.interface))


class PluginAlreadyImplemented(BaseRequirementError):
    """
    Exception that means a plugin implemented a interface that has been already implemented
    """

    def __init__(self, my_plugin, interface, already_plugin):
        super(PluginAlreadyImplemented, self).__init__()
        self.interface = interface
        self.my_plugin = my_plugin
        self.already_plugin = already_plugin

    def __str__(self):
        return 'Plugin %s has tried to implement the interface %s that has' \
               ' already been implemented by %s' % (self.my_plugin, self.interface, self.already_plugin)


class PluginImplementationAbstract(BaseRequirementError):
    """
    Exception that means a plugin implemented a interface that is declared as abstract
    """

    def __init__(self, plugin, interface):
        super(PluginImplementationAbstract, self).__init__()
        self.plugin = plugin
        self.interface = interface

    def __str__(self):
        return 'Plugin %s implement the interface %s that is ' \
               'declared as being abstract' % (self.plugin, self.interface)


class ModuleRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to required Python module being unavailable
    """

    def __init__(self, name, restart):
        super(ModuleRequirementError, self).__init__()
        self.name = name
        self.restart = restart

    def __str__(self):
        if self.restart:
            return 'Dependency "%s" has been installed. Please reload Genesis to use this plugin.' % self.name
        else:
            return 'requires Python module "%s"' % self.name


class CrashedError(BaseRequirementError):
    """
    Exception that means a plugin crashed during load
    """

    def __init__(self, inner):
        super(CrashedError, self).__init__()
        self.inner = inner

    def __str__(self):
        return 'crashed during load: %s' % self.inner


class ImSorryDave(Exception):
    """
    General exception when an attempted operation has a conflict
    """
    def __init__(self, target, depend, reason):
        super(ImSorryDave, self).__init__()
        self.target = target
        self.reason = reason
        self.depend = depend

    def __str__(self):
        if self.reason == 'remove':
            return ('%s can\'t be removed, as %s still depends on it. '
                    'Please remove that first if you would like to remove '
                    'this plugin.' % (self.target, self.depend))
        else:
            return ('%s can\'t be installed, as it depends on %s. Please '
                    'install that first.' % (self.target, self.depend))


class AppInterfaceImplError(BaseRequirementError):
    """
    An app uses a interface that requires a method that the app doesn't provide.
    """
    def __init__(self, app, interface, method):
        super(AppInterfaceImplError, self).__init__()
        self.app = app
        self.interface = interface
        self.method = method

    def __str__(self):
        return ("%s can't be loaded because it doesn't implements the %s method that"
                " the %s interface requires." % (self.app, self.method, self.interface))


class AppRequirementError(BaseRequirementError):
    """
    Exception that means an app wasn't loaded due to required plugin being unavailable
    """

    def __init__(self, name):
        super(AppRequirementError, self).__init__()
        self.name = name

    def __str__(self):
        return 'requires plugin "%s"' % self.name


class AccessDenied(BaseRequirementError):
    """
    There exists an access violation
    """
    def __init__(self, subject, object):
        super(AccessDenied, self).__init__()
        self.subject = subject
        self.object = object

    def __str__(self):
        return "%s cannot use %s" % (self.subject, self.object)