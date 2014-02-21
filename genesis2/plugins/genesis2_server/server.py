import logging
import os

from genesis2.core.core import Plugin
from genesis2.interfaces.gui import IGenesis2Server
from middleware import SessionManager, SessionStore, AuthManager, Dispatcher

try:
    from gevent.pywsgi import WSGIServer
    http_server = 'gevent'
except ImportError:
    from wsgiref.simple_server import make_server
    WSGIServer = lambda adr, **kw: make_server(adr[0], adr[1], kw['application'])
    http_server = 'wsgiref'


def wsgi_application(environ, start_response):
    store = SessionStore.init_safe()

    dispatcher = Dispatcher()
    auth = AuthManager(dispatcher)
    sm = SessionManager(store, auth)

    return sm(environ, start_response)


class Genesis2Server(Plugin):
    def __init__(self):
        super(Genesis2Server, self).__init__()
        self._implements.append(IGenesis2Server)

    def initialize(self, config):
        logger = logging.getLogger('genesis2')

        host = config.get('genesis2', 'bind_host')
        port = config.getint('genesis2', 'bind_port')
        if port is None:
            logger.error('bind_host is mandatory to use genesis2.')
            exit(-1)

        logger.info('Listening on %s:%d.' % (host, port))

        # SSL config setup
        keyfile = config.get('genesis2', 'cert_key')
        certfile = config.get('genesis2', 'cert_file')
        if not os.path.exists(keyfile) or not os.path.isfile(keyfile):
            logger.error('cert_key is mandatory to use genesis2.')
            exit(-1)
        if not os.path.exists(certfile) or not os.path.isfile(certfile):
            logger.error('cert_file is mandatory to use genesis2.')
            exit(-1)

        logger.info('SSL activated')

        self.server = WSGIServer(
            (host, port),
            keyfile=keyfile,
            certfile=certfile,
            application=wsgi_application,
        )

    def serve_forever(self):
        self.server.serve_forever()
