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
from genesis2.core.core import AppManager
from genesis2.core.utils import GenesisManager
from genesis2.utils.config import Config
from genesis2.utils.arkos_platform import detect_platform
from genesis2.utils.filesystem import create_files


def make_log(config_dir):
    base_dir = "/".join(os.path.split(config_dir)[:-1])
    create_files(base_dir, "/log/error.log", "/log/info.log")
    fd = open(config_dir + "/log.conf")

    try:
        dict_config = json.load(fd)
    except ValueError:
        # Shutdown
        print "*** Error in the syntax of log.conf file. ***"
        raise

    logging.config.dictConfig(dict_config)
    logger = logging.getLogger("genesis2")
    logger.info("Logging configuration from %s" % base_dir + "/config/log.conf")
    logger.info("Logging in %s" % base_dir + "/log")


def run_server(config_file=''):
    if config_file != '':
        config_dir = os.path.dirname(config_file)
        if (not os.path.exists(config_dir)) or (not os.path.isdir(config_dir)):
            print "Error in the config file."
    else:
        config_dir = os.getcwd() + "/configs"
        config_file = config_dir + "/genesis.conf"

    make_log(config_dir)
    logger = logging.getLogger("genesis2")
    logger.info('Genesis %s' % version())
    if os.path.isfile(config_file):
        logger.info('Using config file %s' % config_file)
    else:
        # Shutdown
        logger.critical('The %s is not a file.' % config_file)
        exit(-1)

    # Read config
    config = Config()
    if os.path.exists(config_file) and os.path.isfile(config_file):
        config.load(config_file)
    else:
        logger.critical("The %s doesn't exist" % config_file)
        exit(-1)

    genesismgr = GenesisManager(config)

    platform = detect_platform()
    logger.info('Detected platform: %s' % platform)

    # Load plugins
    import genesis2.plugins

    # Load apps
    path_apps = config.get("genesis2", "path_apps", None)
    if path_apps is None:
        path_apps = os.getcwd() + "/apps"
    logger.info("Using %s as path apps." % path_apps)
    appmgr = AppManager(path_apps=path_apps)
    appmgr.load_apps()

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
