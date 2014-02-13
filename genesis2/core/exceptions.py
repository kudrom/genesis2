class BaseRequirementError(Exception):
    """
    Basic exception that means a plugin wasn't loaded due to unmet
    dependencies
    """


class PlatformRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    unsupported platform
    """

    def __init__(self, lst):
        BaseRequirementError.__init__(self)
        self.lst = lst

    def __str__(self):
        return 'requires platforms %s' % self.lst


class GenesisVersionRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    unsupported Genesis version
    """

    def __init__(self, lst):
        BaseRequirementError.__init__(self)
        self.lst = lst

    def __str__(self):
        return 'requires %s' % self.lst


class PluginRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required plugin being unavailable
    """

    def __init__(self, dep):
        BaseRequirementError.__init__(self)
        self.name = dep['name']
        self.package = dep['package']

    def __str__(self):
        return 'requires plugin "%s"' % self.name


class ModuleRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required Python module being unavailable
    """

    def __init__(self, dep, restart):
        BaseRequirementError.__init__(self)
        self.name = dep['name'] if type(dep) == dict else dep
        self.restart = restart

    def __str__(self):
        if self.restart:
            return 'Dependency "%s" has been installed. Please reload Genesis to use this plugin.' % self.name
        else:
            return 'requires Python module "%s"' % self.name


class SoftwareRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required software being unavailable
    """

    def __init__(self, dep):
        BaseRequirementError.__init__(self)
        self.name = dep['name']
        self.pack = dep['package']
        self.bin = dep['binary']

    def __str__(self):
        return 'requires application "%s" (package: %s, executable: %s)' % (self.name, self.pack, self.bin)


class CrashedError(BaseRequirementError):
    """
    Exception that means a plugin crashed during load
    """

    def __init__(self, inner):
        BaseRequirementError.__init__(self)
        self.inner = inner

    def __str__(self):
        return 'crashed during load: %s' % self.inner


class ImSorryDave(Exception):
    """
    General exception when an attempted operation has a conflict
    """
    def __init__(self, target, depend, reason):
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
        self.app = app
        self.interface = interface
        self.method = method

    def __str__(self):
        return ("%s can't be loaded because it doesn't implements the %s method that"
                "the %s interface requires." % (self.app, self.method, self.interface))


class AppRequirementError(BaseRequirementError):
    """
    Exception that means an app wasn't loaded due to
    required plugin being unavailable
    """

    def __init__(self, plugin):
        BaseRequirementError.__init__(self)
        self.name = plugin['name']
        self.package = plugin['package']

    def __str__(self):
        return 'requires plugin "%s"' % self.name


class AccessError(BaseRequirementError):
    """
    There exists an access violation
    """
    def __init__(self, subject, object):
        self.subject = subject
        self.object = object

    def __str__(self):
        return "%s cannot use %s" % (self.subject, self.object)