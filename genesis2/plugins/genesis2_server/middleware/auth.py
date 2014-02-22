from hashlib import sha1
from base64 import b64encode
from passlib.hash import sha512_crypt, bcrypt
import logging
import time

# (kudrom) TODO: Maybe it should be in a utils file
from ..urlhandler import get_environment_vars
from genesis2.core.utils import GenesisManager


def check_password(passw, hashpass):
    """
    Tests if a password is the same as the hash.

    Instance vars:

    - ``passw`` - ``str``, The password in it's original form
    - ``hash`` - ``str``, The hashed version of the password to check against
    """
    if hashpass.startswith('{SHA}'):
        try:
            import warnings
            warnings.warn(
                'SHA1 as a password hash may be removed in a future release.')
            passw_hash = '{SHA}' + b64encode(sha1(passw).digest())
            if passw_hash == hashpass:
                return True
        except:
            import traceback
            traceback.print_exc()
    elif hashpass.startswith('$2a$') and len(hashpass) == 60:
        return bcrypt.verify(passw, hashpass)
    elif sha512_crypt.identify(hashpass):
        return sha512_crypt.verify(passw, hashpass)
    return False


class AuthManager(object):
    """
    Authentication middleware which takes care of user authentication

    Instance vars:

    - ``user`` - `str`, current user logged in or None
    """

    def __init__(self, dispatcher):
        self.session = None
        self.user = None
        self._dispatcher = dispatcher
        self.config = GenesisManager().config

        logger = logging.getLogger('genesis2')

        if self.config.has_section('users'):
            if len(self.config.items('users')) > 0:
                self._enabled = True
            else:
                logger.error('Authentication requested, but no users configured')
        else:
            logger.error('Authentication requested, but no [users] section')

    def deauth(self):
        """
        Deauthenticates current user.
        """
        logger = logging.getLogger('genesis2')
        logger.info('Session closed for user %s' % self.session['auth.user'])
        if self.session is not None:
            # (kudrom) TODO: We should regenerate the sessions here definitely, it's extremly unsecure
            self.session['auth.user'] = None
        else:
            logger.warning('There\'s no session in the environ.')

    def __call__(self, environ, start_response):
        self.session = environ['app.session']
        logger = logging.getLogger('genesis2')

        if environ['PATH_INFO'] == '/auth-redirect':
            start_response('301 Moved Permanently', [('Location', '/')])
            return ''

        self.user = self.session['auth.user'] if 'auth.user' in self.session else None
        if not self._enabled:
            self.user = 'anonymous'
        if self.user is not None or environ['PATH_INFO'].startswith('/dl') \
                or environ['PATH_INFO'].startswith('/middleware'):
            return self._dispatcher(environ, start_response)

        if environ['PATH_INFO'] == '/auth':
            vars_environ = get_environment_vars(environ)
            user = vars_environ.getvalue('username', '')
            if self.config.has_option('users', user):
                pwd = self.config.get('users', user)
                resp = vars_environ.getvalue('response', '')
                if check_password(resp, pwd):
                    logger.info('Session opened for user %s from %s' % (user, environ['REMOTE_ADDR']))
                    self.session['auth.user'] = user
                    start_response('200 OK', [
                        ('Content-type', 'text/plain'),
                        ('X-Genesis-Auth', 'ok'),
                    ])
                    return ''

            logger.error('Login failed for user %s from %s' % (user, environ['REMOTE_ADDR']))
            time.sleep(2)

            start_response('403 Login Failed', [
                ('Content-type', 'text/plain'),
                ('X-Genesis-Auth', 'fail'),
            ])
            return 'Login failed'

        # (kudrom) TODO: I have to enable this
        # templ = self.app.get_template('auth.xml')
        # start_response('200 OK', [('Content-type', 'text/html')])
        # start_response('200 OK', [
        #     ('Content-type', 'text/html'),
        #     ('X-Genesis-Auth', 'start'),
        # ])
        # return templ.render()
