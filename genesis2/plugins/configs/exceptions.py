class ConfFileIsInvalid(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return '%s is not a valid path.' % self.path


class EventIsInvalid(Exception):
    def __init__(self, event):
        self.event = event

    def __str__(self):
        return 'Event %s is invalid.' % self.event


class FileIsNotRegistered(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'File %s is not registered.' % self.path