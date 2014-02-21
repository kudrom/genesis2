import traceback
import os
import logging

import genesis2
# import genesis2.plugins.ui.xslt as xslt
from genesis2.core.core import Plugin, AppManager
from genesis2.core.utils import GenesisManager
# from genesis2.utils.error import format_error
from genesis2.interfaces.gui import IURLHandler, IXSLTFunctionProvider
from genesis2.interfaces.resources import IModuleConfig

from auth import AuthManager


class Dispatcher (object):
    """
    Class representing app state during a request.
    Instance vars:

    - ``config`` - :class:`genesis.config.ConfigProxy` - config for the current user
    - ``gconfig`` - :class:`genesis.config.Config` - global app config
    - ``auth`` - :class:`genesis.middleware.AuthManager` - authentication system
    - ``log`` - :class:`logging.Logger` - app log
    - ``session`` - ``dict`` - full access to the session
    """

    def __init__(self):
        super(Dispatcher, self).__init__()
        config = GenesisManager().config

        self.platform = config.get('platform')
        self.refresh_plugin_data()
        self.template_path = []
        self.less_styles = []
        self.woff_fonts = []
        self.eot_fonts = []
        self.svg_fonts = []
        self.ttf_fonts = []
        self.template_styles = []
        self.template_scripts = []
        self.layouts = {}

    # (kudrom) TODO: Revise all of this
    def refresh_plugin_data(self):
        """
        Rescans plugins for JS, CSS, LESS, XSLT widgets and XML templates.
        """
        self.template_path = []
        self.less_styles = []
        self.woff_fonts = []
        self.eot_fonts = []
        self.svg_fonts = []
        self.ttf_fonts = []
        self.template_styles = []
        self.template_scripts = []
        self.layouts = {}
        includes = []
        functions = {}
        appmgr = AppManager()

        for f in appmgr.grab_apps(IXSLTFunctionProvider):
            functions.update(f.get_funcs())

        # Get path for static content and templates
        apps = appmgr.grab_apps()

        for app in apps:
            path = os.path.join(app.file_path, app)

            fp = os.path.join(path, 'files')
            if os.path.exists(fp):
                self.template_styles.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.css')
                ])
                self.less_styles.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.less')
                ])
                self.woff_fonts.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.woff')
                ])
                self.eot_fonts.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.eot')
                ])
                self.svg_fonts.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.svg')
                ])
                self.ttf_fonts.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.ttf')
                ])
                self.template_scripts.extend([
                    '/dl/'+app+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.js')
                ])

            wp = os.path.join(path, 'widgets')
            if os.path.exists(wp):
                includes.extend([
                    os.path.join(wp, s)
                    for s in os.listdir(wp)
                    if s.endswith('.xslt')
                ])

            lp = os.path.join(path, 'layout')
            if os.path.exists(lp):
                for s in os.listdir(lp):
                    if s.endswith('.xml'):
                        self.layouts['%s:%s' % (app, s)] = os.path.join(lp, s)

            tp = os.path.join(path, 'templates')
            if os.path.exists(tp):
                self.template_path.append(tp)

        # (kudrom) TODO: Change this to the template system
        # if xslt.xslt is None:
        #     xslt.prepare(
        #        includes,
        #        functions
        #     )

    @property
    def config(self):
        if hasattr(self, 'auth'):
            return self.gconfig.get_proxy(self.auth.user)
        else:
            return self.gconfig.get_proxy(None)

    def get_config(self, plugin):
        """
        Returns :class:`genesis.api.ModuleConfig` for a given plugin.
        """
        if plugin.__class__ != type:
            plugin = plugin.__class__
        return self.get_config_by_classname(plugin.__name__)

    def get_config_by_classname(self, name):
        """
        Returns :class:`genesis.api.ModuleConfig` for a given plugin class name.
        """
        cfg = self.get_backend(IModuleConfig,
                               flt=lambda x: x.target.__name__ == name)
        cfg.overlay_config()
        return cfg

    def start_response(self, status, headers=[]):
        self.status = status
        self.headers = headers

    def fix_length(self, content):
        # (kudrom) TODO: maybe move this method to middleware
        has_content_length = False
        for header, value in self.headers:
            if header.upper() == 'CONTENT-LENGTH':
                has_content_length = True
        if not has_content_length:
            self.headers.append(('Content-Length', str(len(content))))

    def __call__(self, environ, start_response):
        """
        Dispatches WSGI requests
        """
        logger = logging.getLogger("genesis2")
        logger.debug('Dispatching %s' % environ['PATH_INFO'])
        self.environ = environ
        self.status = '200 OK'
        self.headers = [('Content-type', 'text/html')]
        self.session = environ['app.session']
        appmgr = AppManager()

        content = 'Sorry, no content for you'
        for handler in appmgr.grab_apps(IURLHandler):
            if handler.match_url(environ):
                try:
                    content = handler.url_handler(self.environ, self.start_response)
                except Exception, e:
                    try:
                        # content = format_error(self, e)
                        pass
                    except:
                        content = 'Fatal error occured:\n' + traceback.format_exc()
                finally:
                    break

        start_response(self.status, self.headers)
        self.fix_length(content)
        content = [content]
        logger.debug('Finishing %s' % environ['PATH_INFO'])
        return content

