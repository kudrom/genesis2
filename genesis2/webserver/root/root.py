import platform
import json

from genesis2.ui import UI, BasicTemplate
from genesis2.core.core import Plugin
from genesis2 import version
from genesis2.interfaces.gui import ICategoryProvider, IProgressBoxProvider
from genesis2.webserver.helpers import EventProcessor, SessionPlugin, event
from genesis2.webserver.urlhandler import URLHandler, url, get_environment_vars
from genesis2.utils import ConfigurationError, shell


class RootDispatcher(URLHandler, SessionPlugin, EventProcessor, Plugin):
    # Plugin folders. This dict is here forever^W until we make MUI support
    folders = {
        'cluster': 'CLUSTER',
        'system': 'SYSTEM',
        'hardware': 'HARDWARE',
        'apps': 'APPLICATIONS',
        'servers': 'SERVERS',
        'tools': 'TOOLS',
        'advanced': 'ADVANCED',
        'other': 'OTHER',
    }

    # Folder order
    folder_ids = ['cluster', 'apps', 'servers', 'system', 'hardware', 'tools', 'advanced', 'other']

    def on_session_start(self):
        self._cat_selected = 'firstrun' if self.is_firstrun() else 'dashboard'
        self._about_visible = False
        self._module_config = None

    def is_firstrun(self):
        return not self.app.gconfig.has_option('genesis', 'firstrun')

    def main_ui(self):
        self.selected_category.on_init()
        templ = self.app.inflate('middleware:main')

        if self.app.config.get('genesis', 'nofx', '') != '1':
            templ.remove('fx-disable')

        if self._about_visible:
            templ.append('main-content', self.get_ui_about())

        templ.append('main-content', self.selected_category.get_ui())

        if 'messages' in self.app:
            for msg in self.app.session['messages']:
                templ.append(
                    'system-messages',
                    UI.SystemMessage(
                        cls=msg[0],
                        text=msg[1],
                    )
                )
            del self.app.session['messages']
        return templ

    def do_init(self):
        # end firstrun wizard
        if self._cat_selected == 'firstrun' and not self.is_firstrun():
            self._cat_selected = 'dashboard'

        cat = None
        for c in self.app.grab_plugins(ICategoryProvider):
            # initialize current plugin
            if c.plugin_id == self._cat_selected:
                cat = c
        self.selected_category = cat

    def get_ui_about(self):
        ui = self.app.inflate('middleware:about')
        ui.find('ver').set('text', version())
        return ui

    @url('^/middleware/progress$')
    def serve_progress(self, req, sr):
        r = []
        if 'statusmsg' in self.app:
            for msg in self.app.session['statusmsg']:
                r.append({
                    'id': msg[0],
                    'type': 'statusbox',
                    'owner': msg[0],
                    'status': msg[1]
                })
            del self.app.session['statusmsg']
        for p in sorted(self.app.grab_plugins(IProgressBoxProvider)):
            if p.has_progress():
                r.append({
                    'id': p.plugin_id,
                    'type': 'progressbox',
                    'owner': p.title,
                    'status': p.get_progress(),
                    'can_abort': p.can_abort
                })
        return json.dumps(r)

    @url('^/middleware/styles.less$')
    def serve_styles(self, req, sr):
        r = ''
        for s in sorted(self.app.less_styles):
            r += '@import "%s";\n' % s
        return r
    
    @url('^/$')
    def process(self, req, start_response):
        self.do_init()

        templ = self.app.get_template('index.xml')

        cat = None
        v = UI.VContainer(spacing=0)

        # Sort plugins by name
        cats = self.app.grab_plugins(ICategoryProvider)
        cats = sorted(cats, key=lambda p: p.text)

        for fld in self.folder_ids:
            cat_vc = UI.VContainer(spacing=0)
            if self.folders[fld] == '':
                # Omit wrapper for special folders
                cat_folder = cat_vc
            else:
                cat_folder = UI.CategoryFolder(cat_vc,
                                               text=self.folders[fld],
                                               icon='/dl/middleware/ui/catfolders/' + fld + '.png'
                                               if self.folders[fld] != '' else '',
                                               id=fld
                                               )
            # cat_vc will be VContainer or CategoryFolder

            exp = False
            empty = True
            for c in cats:
                # Put corresponding plugins in this folder
                if c.folder == fld:
                    empty = False
                    if c == self.selected_category:
                        exp = True
                    cat_vc.append(UI.Category(
                        iconfont=c.iconfont,
                        name=c.text,
                        id=c.plugin_id,
                        counter=c.get_counter(),
                        selected=c == self.selected_category
                    ))

            if not empty:
                v.append(cat_folder)
            cat_folder['expanded'] = exp

        for c in cats:
            if c.folder in ['top', 'bottom']:
                templ.append(
                    'topplaceholder-'+c.folder,
                    UI.TopCategory(
                        text=c.text,
                        id=c.plugin_id,
                        iconfont=c.iconfont,
                        counter=c.get_counter(),
                        selected=(c == self.selected_category)
                    )
                )

        templ.append('_head', UI.HeadTitle(text='Genesis @ %s' % platform.node()))
        templ.append('leftplaceholder', v)
        templ.append('version', UI.Label(text=('Genesis ' + version()), size=2))
        templ.insertText('cat-username', self.app.auth.user)
        templ.appendAll('links', 
                        UI.LinkLabel(iconfont='gen-info', text='About', id='about'),
                        UI.OutLinkLabel(iconfont='gen-certificate',
                                        text='License',
                                        url='http://www.gnu.org/licenses/gpl.html'
                                        )
                        )

        return templ.render()

    @url('^/session_reset$')
    def process_reset(self, req, start_response):
        self.app.session.clear()
        start_response('301 Moved Permanently', [('Location', '/')])
        return ''

    @url('^/logout$')
    def process_logout(self, req, start_response):
        self.app.auth.deauth()
        start_response('301 Moved Permanently', [('Location', '/')])
        return ''

    @url('^/embapp/.+')
    def goto_embed(self, req, start_response):
        path = req['PATH_INFO'].split('/')
        host = req['HTTP_HOST']
        bhost = req['HTTP_HOST'].split(':')[0]
        ssl = False

        try:
            if path[3] == 'ssl':
                ssl = True
        except IndexError:
            pass

        content = self.app.inflate('middleware:embapp')
        content.insertText('ea-port', ':' + path[2])
        content.find('ea-link').set('href', req['wsgi.url_scheme']+'://'+host)
        content.append('ea-frame-container',
                       UI.IFrame(id='ea-frame',
                                 src=('https://' if ssl else 'http://') + bhost + ':' + path[2]
                                 )
                       )
        self._cat_selected = 'dashboard'
        return content.render()

    @event('category/click')
    def handle_category(self, event, params, **kw):
        if not isinstance(params, list):
            return
        if len(params) != 1:
            return

        self._cat_selected = 'firstrun' if self.is_firstrun() else params[0]
        self.do_init()

    @event('linklabel/click')
    def handle_linklabel(self, event, params, vars=None):
        if params[0] == 'about':
            self._about_visible = True

    @event('button/click')
    def handle_btns(self, event, params, vars=None):
        if params[0] == 'aborttask':
            for p in self.app.grab_plugins(IProgressBoxProvider):
                if p.plugin_id == params[1] and p.has_progress():
                    p.abort()
        if params[0] == 'gen_reload':
            self.app.restart()
        if params[0] == 'gen_shutdown':
            shell('shutdown -P now')
        if params[0] == 'gen_reboot':
            shell('reboot')

    @event('dialog/submit')
    def handle_dlg(self, event, params, vars=None):
        if params[0] == 'dlgAbout':
            self._about_visible = False

    @url('^/handle/.+')
    def handle_generic(self, req, start_response):
        # Iterate through the IEventDispatchers and find someone who will take care of the event
        # TODO: use regexp for shorter event names, ex. 'btn_clickme/click'
        path = req['PATH_INFO'].split('/')
        event = '/'.join(path[2:4])
        params = path[4:]

        try:
            self.do_init()
            self.selected_category.on_init()
        except ConfigurationError, e:
            # ignore problems if we are leaving the plugin anyway
            if params[0] == self._cat_selected or event != 'category/click':
                raise

        # Current module
        cat = self.app.grab_plugins(ICategoryProvider, lambda x: x.plugin_id == self._cat_selected)[0]

        # Search self and current category for event handler
        vars = get_environment_vars(req)
        for handler in (cat, self):
            if handler.match_event(event):
                result = handler.event(event, params, vars=vars)
                if isinstance(result, str):
                    # For AJAX calls that do not require information
                    # just return ''
                    return result
                if isinstance(result, BasicTemplate):
                    # Useful for inplace AJAX calls (that returns partial page)
                    return result.render()

        # We have no result or handler - return default page
        main = self.main_ui()
        return main.render()
