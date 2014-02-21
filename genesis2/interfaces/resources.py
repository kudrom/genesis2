from genesis2.core.utils import Interface


class IConfigurable (Interface):
    """
    Interface for Configurables. Configurable is an entity (software or
    system aspect) which has a set of config files.

    - ``name`` - `str`, a human-readable name.
    - ``id`` - `str`, unique ID.
    """
    name = None
    id = None

    def list_files(self):
        """
        Implementation should return list of config file paths - file names or
        wildcards (globs) which will be expanded by :func:`glob.glob`.
        """


class IConfMgrHook (Interface):
    """
    Base interface for ConfManager hooks that react to events and process
    the config files.
    """
    def pre_load(self, cfg, path):
        """
        Called before reading a file.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        """

    def post_load(self, cfg, path, data):
        """
        Called after reading a file. Implementation has to process the file and
        return new content

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        :rtype:         str
        :returns:       modified contents
        """

    def pre_save(self, cfg, path, data):
        """
        Called before saving a file. Implementation has to process the file and
        return new content.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        :rtype:         str
        :returns:       modified contents
        """

    def post_save(self, cfg, path):
        """
        Called after saving a file.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        """

    def finished(self, cfg):
        """
        Called when a ``commit`` is performed. Good time to make backups/save data/etc.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        """


class IModuleConfig (Interface):
    """
    Base interface for module configurations.

    See :class:`genesis.api.ModuleConfig`
    """


class IComponent (Interface):
    """
    Base interface for background components.

    See :class:`Component`.
    """
    def run(self):
        pass

