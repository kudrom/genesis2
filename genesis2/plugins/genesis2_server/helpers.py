import inspect
import traceback

from genesis2.core.core import Plugin, implements
from genesis2.ui import UI
from genesis2 import apis
from genesis2.interfaces.gui import IEventDispatcher, ICategoryProvider
from genesis2.interfaces.resources import IModuleConfig


def event(event_name):
    """
        Decorator which implements a mechanism later used by EventProcessor
        It's used by a plugin that wants to register a callback for a certain
        event.
    """
    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    locals = frame.f_locals

    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError('@event() can only be used in class definition')

    loc_events = locals.setdefault('_events', {})

    def event_decorator(func):
        loc_events[event_name] = func
        return func

    return event_decorator


class EventProcessor(object):
    """
    A base class for plugins suitable for handling UI Events_.
    You will need to decorate handler methods with :func:`event`.
    """
    implements(IEventDispatcher)

    def _get_event_handler(self, event):
        """
            Private method to retrieve the proper method registered with the
            event provided as first argument
        """
        for cls in self.__class__.mro():
            if '_events' in dir(cls):
                if event in cls._events:
                    return cls._events[event]
        return None

    def match_event(self, event):
        """
            Returns True if class (or any parent class) could handle event
        """
        if self._get_event_handler(event) is not None:
            return True
        return False

    def event(self, event, *params, **kwparams):
        """
            Calls a handler method suitable for given event.
        """
        handler = self._get_event_handler(event)
        if handler is None:
            return None
        return handler(event, *params, **kwparams)


# (kudrom) TODO: Disconnect self.app with a session manager
class SessionPlugin(Plugin):
    """
    A base class for plugins attached to the current user's session.

    Instance variables starting with '_' will be automatically [re]stored
    from/into the session.

    """

    session_proxy = None

    def __init__(self):
        if self.session_proxy is None:
            self.session_proxy = self.app.session.proxy(self.__class__.__name__)

        if self.session_proxy.get('sp_estabilished', None) is None:
            self.session_proxy['sp_estabilished'] = 'yes'
            try:
                self.on_session_start()
            except Exception:
                traceback.print_exc()
                raise

    def __getattr__(self, name):
        # TODO: use regexps
        if name[0] == '_' and not name[1] == '_':
            return self.session_proxy.get(name, None)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

    def __setattr__(self, name, value):
        # TODO: use regexps
        if name[0] == '_' and not name[1] == '_':
            self.session_proxy[name] = value
        else:
            self.__dict__[name] = value

    def on_session_start(self):
        """
        Called when a session is estabilished for new user or a new plugin
        is attached to the session for the first time.
        """


class CategoryPlugin(SessionPlugin, EventProcessor):
    """
    A base class for plugins providing sidebar entry

    - ``text`` - `str`, sidebar entry text
    - ``iconfont`` - `str`, sidebar iconfont class
    - ``folder`` - `str`, sidebar section name (lowercase)
    """
    abstract = True

    implements(ICategoryProvider)

    text = 'Caption'
    iconfont = 'gen-question'
    folder = 'other'

    def on_init(self):
        """
        Called when a web request has arrived and this plugin is active (visible).
        """

    def get_counter(self):
        """
        May return short string to be displayed in 'bubble' right to the sidebar
        entry.

        :returns: None or str
        """

    def get_config(self):
        """
        Returns a most preferred ModuleConfig for this class.

        :returns:   :class:`ModuleConfig` or None
        """
        try:
            return self.app.get_config(self)
        except:
            return None

    def put_message(self, cls, msg):
        """
        Pushes a visual message to the message queue.
        All messages will be displayed on the next webpage update user will
        receive.

        :param  cls:    one of 'info', 'warn', 'err'
        :type   cls:    str
        :params msg:    message text
        """
        if not 'messages' in self.app.session:
            self.app.session['messages'] = []
        self.app.session['messages'].append((cls, msg))

    def put_statusmsg(self, msg):
        """
        Sets a blocking status message to appear while an operation completes.
        """
        if not self.app.session.has_key('statusmsg'):
            self.app.session['statusmsg'] = []
        self.app.session['statusmsg'].append((self.text, msg))

    def clr_statusmsg(self):
        """
        Clear the currently shown status window
        """
        if not self.app.session.has_key('statusmsg'):
            self.app.session['statusmsg'] = []
        self.app.session['statusmsg'].append((self.text, False))

    # (kudrom) TODO: Redirect with JS? The URL is registered in genesis2_server.root.root
    def redirapp(self, service, port, ssl=False):
        if self.app.get_backend(apis.services.IServiceManager).get_status(service) == 'running':
            if ssl:
                return UI.JS(code='window.location.replace("/embapp/' + str(port) + '/ssl")')
            else:
                return UI.JS(code='window.location.replace("/embapp/' + str(port) + '")')
        else:
            return UI.DialogBox(UI.Label(text='The service %s is not '
                                              'running. Please start the service with the Status button '
                                              'before continuing.' % service), hidecancel=True)

    def update_services(self):
        apis.networkcontrol(self.app).port_changed(self)
