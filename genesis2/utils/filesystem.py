import os


def unlink_recursive(dir):
    if os.path.isdir(dir):
        for file in os.listdir(dir):
            file_path = os.path.join(dir, file)
            if os.path.isdir(file_path):
                unlink_recursive(file_path)
            else:
                os.unlink(file_path)
        os.rmdir(dir)
    else:
        os.unlink(dir)


def create_files(*files, **kwargs):
    base_dir = os.getcwd() if 'base_dir' not in kwargs else kwargs['base_dir']
    mode = 0777 if 'mode' not in kwargs else kwargs['mode']
    for file in files:
        # Allow calling create_files with base_dir and a file starting with /
        if file[0] == '/' and 'base_dir' in kwargs:
            file = file[1:]
        # Interpret a calling without base_dir and a start different to /
        if 'base_dir' not in kwargs and file[0] != '/' and not file.startswith('./'):
            file = '/' + file
        path = os.path.join(base_dir, file)
        file_dir = os.path.dirname(path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir, mode)
        if os.path.isdir(file_dir):
            open(path, "a").close()
