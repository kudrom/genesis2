import os
import logging


def unlink_recursive(path):
    """
    from https://stackoverflow.com/questions/185936/delete-folder-contents-in-python
    """
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception, e:
            logger = logging.getLogger("genesis2")
            logger.error(e.message)


def create_files(base_dir='', mode=0777, *files):
    for file in files:
        path = base_dir + file
        file_dir = os.path.dirname(path)
        if not os.path.exists(file_dir):
            os.makedirs(path, mode)
        if os.path.isdir(file_dir):
            open(path, "a").close()
