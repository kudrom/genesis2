from genesis2.ui import *
from genesis2.core.core import implements, Plugin
from updater import FeedUpdater
from genesis2.interfaces.gui import IWidget

class NewsWidget(Plugin):
    implements(IWidget)
    title = 'Project news'
    iconfont = 'gen-bullhorn'
    name = 'Project news'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        ui = self.app.inflate('middleware:news')
        feed = FeedUpdater.get().get_feed()
        if feed is not '':
            for i in sorted(feed, key=lambda dt: dt['time'], reverse=True):
                ui.append('list',
                          UI.CustomHTML(html='<a href="%s" target="_blank"><li>%s</li></a>' % (i['link'], i['title'])))
        return ui

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None

    def process_config(self, event, params, vars):
        pass
