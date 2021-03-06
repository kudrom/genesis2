# encoding: utf-8
#
# Copyright (C) 2010 Dmitry Zamaruev (dmitry.zamaruev@gmail.com)


"""
This module provides simple session handling and WSGI Middleware.
You should instantiate SessionStore, and pass it to WSGI middleware along with next WSGI application in chain.
"""
import os
import time
import Cookie
import hashlib
from genesis2.utils.interlocked import ClassProxy


def sha1(var):
    return hashlib.sha1(str(var)).hexdigest()


class SessionProxy(object):
    """
    SessionProxy used to automatically add prefixes to keys
    """
    def __init__(self, session, prefix):
        self._session = session
        self._prefix = prefix + '-'

    def __getitem__(self, key):
        return self._session[self._prefix + key]

    def __setitem__(self, key, value):
        self._session[self._prefix + key] = value

    def get(self, key, default=None):
        return self._session.get(self._prefix + key, default)


class Session(dict):
    """
    Session object. Holds data between requests
    """

    def __init__(self, id, **kwargs):
        super(Session, self).__init__(**kwargs)
        self._id = id
        self._creationTime = self._accessTime = time.time()

    @property
    def id(self):
        """ Session ID """
        return self._id

    @property
    def creation_time(self):
        """ Session create time """
        return self._creationTime

    @property
    def access_time(self):
        """ Session last access time """
        return self._accessTime

    def touch(self):
        self._accessTime = time.time()

    def proxy(self, prefix):
        return SessionProxy(self, prefix)

    @staticmethod
    def generate_id():
        return sha1(os.urandom(40))


class SessionStore(object):
    """
    Manages multiple session objects
    """
    # TODO: add session deletion/invalidation
    def __init__(self, timeout=30):
        # Default timeout is 30 minutes
        # Use internal timeout in seconds (for easier calculations)
        self._timeout = timeout*60
        self._store = {}

    @staticmethod
    def init_safe():
        """ Create a thread-safe SessionStore """
        return ClassProxy(SessionStore())

    def create(self):
        """
        Create a new session, you should commit session to save it for future
        """
        sess_id = Session.generate_id()
        return Session(sess_id)

    def checkout(self, id):
        """
        Checkout session for use, you should commit session to save it for future
        """
        sess = self._store.get(id)

        if sess is not None:
            sess.touch()

        return sess

    def commit(self, session):
        """
        Saves session for future use (useful in database backends)
        """
        self._store[session.id] = session

    def vacuum(self):
        """
        Goes through all sessions and deletes all old sessions.
        Should be called periodically
        """
        ctime = time.time()
        # We should use .keys() here, because we could change size of dict
        for sessId in self._store.keys():
            if (ctime - self._store[sessId].access_time) > self._timeout:
                del self._store[sessId]


class SessionManager(object):
    """
    Session middleware. Takes care of creation/checkout/commit of a session.
    Sets 'app.session' variable inside WSGI environment.
    """
    # TODO: Add cookie expiration and force expiration
    # TODO: Add deletion of invalid session
    def __init__(self, store, wsgi_application):
        """ Initializes SessionManager

        @store - instance of SessionStore
        @application - wsgi dispatcher callable
        """
        self._session_store = store
        self._application = wsgi_application
        self._session = None
        self._start_response_args = ('200 OK', [])

    def add_cookie(self, headers):
        if self._session is None:
            raise RuntimeError('Attempt to save non-initialized session!')

        sess_id = self._session.id
        cookie = Cookie.SimpleCookie()
        cookie['sess'] = sess_id
        cookie['sess']['path'] = '/'

        headers.append(('Set-Cookie', cookie['sess'].OutputString()))

    def start_response(self, status, headers):
        self.add_cookie(headers)
        self._start_response_args = (status, headers)

    def _load_session_cookie(self, environ):
        cookie = Cookie.SimpleCookie(environ.get('HTTP_COOKIE'))
        cookie = cookie.get('sess')
        if cookie is not None:
            self._session = self._session_store.checkout(cookie.value)

    def _get_client_id(self, environ):
        hash = 'salt'
        hash += environ.get('REMOTE_ADDR', '')
        hash += environ.get('REMOTE_HOST', '')
        hash += environ.get('HTTP_USER_AGENT', '')
        hash += environ.get('HTTP_HOST', '')
        return sha1(hash)

    def _get_session(self, environ):
        # Load session from cookie
        self._load_session_cookie(environ)

        # Check is session exists and valid
        client_id = self._get_client_id(environ)
        if self._session is not None:
            if self._session.get('client_id', '') != client_id:
                self._session = None

        # Create session
        if self._session is None:
            self._session = self._session_store.create()
            self._session['client_id'] = client_id

        return self._session

    def __call__(self, environ, start_response):
        self.start_response_origin = start_response
        self._session_store.vacuum()
        sess = self._get_session(environ)
        environ['app.session'] = sess

        result = None
        try:
            result = self._application(environ, self.start_response)
        finally:
            self._session_store.commit(self._session)

        self.start_response_origin(*self._start_response_args)
        return result
