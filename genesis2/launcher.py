import os
import logging
import logging.config
import json

try:
    from gevent.pywsgi import WSGIServer
    http_server = 'gevent'
except ImportError:
    from wsgiref.simple_server import make_server
    WSGIServer = lambda adr, **kw: make_server(adr[0], adr[1], kw['application'])
    http_server = 'wsgiref'

from genesis2 import version
from genesis2.core.core import AppManager, GenesisManager
from genesis2.utils.config import Config
from genesis2.webserver.middleware import AppDispatcher
import genesis2.utils


def make_log():
    working_directory = os.path.dirname(__file__)
    if os.path.exists(working_directory + "/log") and os.path.isdir(working_directory + "/log"):
        if not os.path.isfile(working_directory + "/log/error.log"):
            open(working_directory + "/log/error.log").close()
        if not os.path.isfile(working_directory + "/log/info.log"):
            open(working_directory + "/log/info.log").close()
    else:
        os.mkdir(working_directory + "/log")
        open(working_directory + "/log/error.log").close()
        open(working_directory + "/log/info.log").close()

    if os.path.exists(working_directory + "/configs" and os.path.isdir(working_directory + "/configs")):
        if not os.path.isfile(working_directory + "/configs/log.conf"):
            open(working_directory + "/configs/log.conf").close()
    else:
        os.mkdir(working_directory + "/log")
        open(working_directory + "/configs/log.conf").close()

    try:
        config = json.load(working_directory + "/configs/log.conf")
    except ValueError:
        # Shutdown
        print "Error in the syntax of log.conf file."
        raise

    logging.config.dictConfig(config)
    logger = logging.getLogger("genesis2")
    logger.info("Logging in %s" % working_directory)


def run_server(log_level=logging.INFO, config_file=''):
    make_log(debug=(log_level == logging.DEBUG), log_level=log_level)
    logger = logging.getLogger("genesis2")
    logger.info('Genesis %s' % version())

    genesismgr = GenesisManager()

    # Read config
    config = Config()
    if config_file:
        logger.info('Using config file %s' % config_file)
        config.load(config_file)
    else:
        logger.info('Using default settings')

    # (kudrom) TODO: Do this on GenesisManager
    config.set('log_facility', logger)

    # (kudrom) TODO: Check this
    platform = genesis2.utils.detect_platform()
    logger.info('Detected platform: %s' % platform)

    # Load plugins
    from genesis2.plugins import *

    # Load apps
    path_apps = config.get("genesis2", "path_apps", None)
    if path_apps is not None:
        AppManager(path_apps=path_apps)
    else:
        path_apps = "/".join((__file__.split("/")[:-1])) + "/apps"
        logger.info("Using default path apps %s" % path_apps)

    # (kudrom) TODO: Register a new ComponentMgr

    # (kudrom) TODO: we should use an iptables plugin
    # Make sure correct kernel modules are enabled
    # genesis2.utils.shell('modprobe ip_tables')

    # Start server
    # host = config.get('genesis', 'bind_host')
    # port = config.getint('genesis', 'bind_port')
    # log.info('Listening on %s:%d' % (host, port))

    # (kudrom) TODO: SSL by default
    # SSL params
    # ssl = {}
    # if config.getint('genesis', 'ssl') == 1:
    #     ssl = {
    #         'keyfile':  config.get('genesis', 'cert_key'),
    #         'certfile': config.get('genesis', 'cert_file'),
    #     }

    # log.info('Using HTTP server: %s' % http_server)

    # server = WSGIServer(
    #     (host, port),
    #     application=AppDispatcher(config).dispatcher,
    #     **ssl
    # )

    # config.set('server', server)

    # (kudrom) TODO: In arch the syslog-ng service is disabled by default
    # try:
    #     syslog.openlog(
    #         ident='genesis',
    #         facility=syslog.LOG_AUTH,
    #     )
    # except:
    #     syslog.openlog('genesis')

    # log.info('Starting server')

    # server.serve_forever()

    # (kudrom) TODO: What the hell is this?
    # if hasattr(server, 'restart_marker'):
    #     log.info('Restarting by request')

        # Close all descriptors. Creepy thing
    #     fd = 20
    #     while fd > 2:
    #         try:
    #             os.close(fd)
    #             log.debug('Closed descriptor #%i' % fd)
    #         except:
    #             pass
    #         fd -= 1

    #     os.execv(sys.argv[0], sys.argv)
    # else:
    #     log.info('Stopped by request')
