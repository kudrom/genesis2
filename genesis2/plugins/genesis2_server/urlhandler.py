import re
import cgi
import inspect

from genesis2.interfaces.gui import IURLHandler
from genesis2.core.core import Plugin


def url(uri):
    """ Decorator function to register URL handlers
    """
    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    locals = frame.f_locals

    if ((locals is frame.f_globals) or
        ('__module__' not in locals)):
        raise TypeError('@url() can only be used in class definition')

    loc_urls = locals.setdefault('_urls',{})

    def url_decorator(func):
        loc_urls[re.compile(uri)] = func.__name__
        return func

    return url_decorator


class URLHandler(Plugin):
    """
    Base class that handles HTTP requests based on its methods decorated with
    :func:url
    """

    def __init__(self):
        super(URLHandler, self).__init__()
        self._implements.append(IURLHandler)

    def _get_url_handler(self, uri):
        for cls in self.__class__.mro():
            if '_urls' in dir(cls):
                for uri_re in cls._urls.keys():
                    if uri_re.match(uri):
                        return cls._urls[uri_re]
        return None

    def match_url(self, req):
        """ Returns True if class (or any parent class) could handle URL
        """
        if self._get_url_handler(req.get('PATH_INFO')) is not None:
            return True
        return False

    def url_handler(self, req, start_response):
        handler = self._get_url_handler(req.get('PATH_INFO'))
        if handler is None:
            return
        try:
            handler = self.__getattribute__(handler)
        except AttributeError:
            return

        return handler(req, start_response)


def get_environment_vars(req):
    """
    Extracts POST data from WSGI environment

    :rtype: :class:`cgi.FieldStorage`
    """
    res = None
    req.setdefault('QUERY_STRING', '')
    if req['REQUEST_METHOD'].upper() == 'POST':
        ctype = req.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
        if ctype.startswith('application/x-www-form-urlencoded') \
           or ctype.startswith('multipart/form-data'):
            res = cgi.FieldStorage(fp=req['wsgi.input'],
                                   environ=req,
                                   keep_blank_values=1)
    else:
        res = cgi.FieldStorage(environ=req, keep_blank_values=1)

    return res
