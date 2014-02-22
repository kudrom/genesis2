import os
import logging
import logging.config
import json

from genesis2 import version
from genesis2.core.core import AppManager
from genesis2.core.utils import GenesisManager
from genesis2.utils.config import Config
from genesis2.utils.arkos_platform import detect_platform
from genesis2.utils.filesystem import create_files


def make_log(config_dir):
    # (kudrom) TODO: Rotate the logs
    base_dir = os.path.dirname(config_dir)
    create_files("/log/error.log", "/log/info.log", base_dir=base_dir)
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

    # (kudrom) TODO: I should delete the GenesisManager and substitute it with a Plugin
    GenesisManager(config)

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

    if not hasattr(genesis2.apis, 'PGenesis2Server'):
        logger.error('There\'s no plugin for PGenesis2Server registered in the system')
        exit(-1)

    # The server is a plugin to ease its replacement
    logger.info('Starting server')
    server = getattr(genesis2.apis, 'PGenesis2Server')
    server.initialize(config)
    server.serve_forever()

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
