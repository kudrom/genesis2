import logging
from logging.handlers import MemoryHandler


def stop_server():
    logger = logging.getLogger("genesis2")

    # Save to disk the memory logs with an explicit call (just to be sure)
    for handler in logger.handlers:
        if isinstance(handler, MemoryHandler):
            handler.flush()

    exit(-1)
