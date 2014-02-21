from genesis2.core.utils import Interface


class IGenesis2Server(Interface):
    pass


class ICategoryProvider (Interface):
    """
    Base interface for plugins that provide a sidebar entry

    See :class:`genesis.api.CategoryPlugin`
    """
    def get_ui(self):
        """
        Should return :class:`genesis.ui.Layout` or :class:`genesis.ui.Element`
        representing plugin's UI state
        """


class IEventDispatcher (Interface):
    """
    Base interface for :class:`Plugin` which may dispatch UI Events_.

    See :class:`genesis.api.EventProcessor`
    """

    def match_event(self, event):
        pass

    def event(self, event, *params, **kwparams):
        pass


class IXSLTFunctionProvider (Interface):
    """
    Interface for classes which provide additional XSLT functions for
    use in Widgets_ templates.
    """

    def get_funcs(self):
        """
        Gets all XSLT functions provided. Functions are subject to be invoked
        by ``lxml``.

        :returns: dict(str:func)
        """


class IMeter (Interface):
    pass


class IProgressBoxProvider(Interface):
    """
    Allows your plugin to show a background progress dialog

    - ``iconfont`` - `str`, iconfont class
    - ``title`` - `str`, text describing current activity
    """
    iconfont = ""
    title = ""

    def has_progress(self):
        """
        :returns:       whether this plugin has any currently running activity
        """
        return False

    def get_progress(self):
        """
        :returns:       text describing activity's current status
        """
        return ''

    def can_abort(self):
        """
        :returns:       whether currently running activity can be aborted
        """
        return False

    def abort(self):
        """
        Should abort current activity
        """


class IURLHandler(Interface):
    """
    Base interface for classes that can handle HTTP requests
    """

    def match_url(self, req):
        """
        Determines if the class can handle given request.

        :param  req:    WSGI request environment
        :type   req:    dict
        :rtype:         bool
        """

    def url_handler(self, req, sr):
        """
        Should handle given request.

        :param  req:    WSGI request environment
        :type   req:    dict
        :param  sr:     start_response callback for setting HTTP code and headers
        :type   sr:     func(code, headers)
        :returns:       raw response body
        :rtype:         str
        """


class IWidget(Interface):
    """
    Interface for a dashboard widget

    - ``iconfont`` - `str`, iconfont class
    - ``title`` - `str`, short title text
    - ``name`` - `str`, name shown in 'choose widget' dialog
    - ``style`` - `str`, 'normal' and 'linear' now supported
    """
    title = ''
    name = ''
    iconfont = ''
    style = 'normal'

    def get_ui(self, cfg, id=None):
        """
        Returns plugin UI (Layout or Element)

        :param  id:     plugin ID
        :type   id:     str
        :param  cfg:    saved plugin configuration
        :type   cfg:    str
        """

    def handle(self, event, params, cfg, vars=None):
        """
        Handles UI event of a plugin

        :param  cfg:    saved plugin configuration
        :type   cfg:    str
        """

    def get_config_dialog(self):
        """
        Returns configuration dialog UI (Layout or Element), or None
        """

    def process_config(self, vars):
        """
        Saves configuration from the configuration dialog (get_config_dialog)

        :rtype   cfg:    str
        """


class ISysStat(Interface):
    def get_load(self):
        pass

    def get_ram(self):
        pass

    def get_swap(self):
        pass
