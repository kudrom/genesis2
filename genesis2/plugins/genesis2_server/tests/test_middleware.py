import mock
from mock import patch
import gc
from unittest import TestCase

from genesis2.plugins.genesis2_server.middleware.session import SessionStore, SessionManager, Session, sha1


class TestsSessionMiddleware(TestCase):
    def setUp(self):
        def wsgi_application(environ, start_response):
            headers = []
            start_response('200 OK', headers)
            environ['app.session']['testing'] = True
            return "hello world", headers

        self.wsgi_app = wsgi_application
        self.store = SessionStore.init_safe()
        self.smgr = SessionManager(self.store, self.wsgi_app)
        self.environ = {}

    def test_correct(self):
        self.assertNotIn('HTTP_COOKIE', self.environ)

        start_response = mock.MagicMock()
        ret, headers = self.smgr(self.environ, start_response)

        self.assertIn('app.session', self.environ)
        self.assertIsInstance(self.environ['app.session'], Session)
        self.assertIn('testing', self.environ['app.session'])
        self.assertTrue(self.environ['app.session']['testing'])

        self.assertIn('client_id', self.environ['app.session'])
        self.assertEqual(self.environ['app.session']['client_id'], sha1('salt'))

        self.assertIn('Set-Cookie', map(lambda x: x[0], headers))
        cookies = filter(lambda x: x[0] == 'Set-Cookie', headers)
        for cookie in cookies:
            self.assertIn('sess', cookie[1])
        self.assertEqual(ret, 'hello world')

    def test_already_cookie_good_client(self):
        start_response = mock.MagicMock()
        sess = self.store.create()
        sess['client_id'] = sha1('salt')
        self.smgr._session_store.commit(sess)
        self.smgr._session = sess
        self.environ['HTTP_COOKIE'] = 'sess=' + sess._id + '; Path=/'
        ret, headers = self.smgr(self.environ, start_response)

        self.assertEqual(self.environ['app.session']._id, sess._id)
        self.assertIn(sess._id, headers[0][1])

    def test_already_cookie_bad_client(self):
        start_response = mock.MagicMock()
        sess = self.smgr._session_store.create()
        self.smgr._session_store.commit(sess)
        self.smgr._session = sess
        self.environ['HTTP_COOKIE'] = 'sess=' + sess._id + '; Path=/'
        self.smgr(self.environ, start_response)

        self.assertNotEqual(self.environ['app.session']._id, sess._id)

    def test_timeout(self):
        start_response = mock.MagicMock()
        sess = self.store.create()
        sess['client_id'] = sha1('salt')
        self.smgr._session_store.commit(sess)
        self.smgr._session = sess
        self.environ['HTTP_COOKIE'] = 'sess=' + sess._id + '; Path=/'
        self.smgr(self.environ, start_response)

        self.assertIsNotNone(self.store.checkout(sess._id))
        with patch('time.time') as time:
            time.return_value = 99999999999999.99
            self.store.vacuum()
            gc.collect()
            self.assertIsNone(self.store.checkout(sess._id))

    def test_session_proxy(self):
        sess = Session('')
        proxy = sess.proxy('test')
        proxy['123'] = 'value'

        self.assertIn('test-123', sess)
        self.assertEqual(sess['test-123'], 'value')


class AuthMiddleware(TestCase):
    def test_dauth(self):
        pass


class DispatcherMiddleware(TestCase):
    pass