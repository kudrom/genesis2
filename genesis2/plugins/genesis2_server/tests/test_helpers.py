from unittest import TestCase

from genesis2.webserver.helpers import event, EventProcessor


class TestEvent(TestCase):
    def setUp(self):
        class A(object):
            @event('some/event')
            def test1(self):
                pass

            @event('other/event')
            def test2(self):
                pass
        self.A = A

    def test_functional(self):
        self.assertIn('some/event', self.A._events)
        self.assertIn('other/event', self.A._events)

    def test_scope(self):
        self.assertRaises(TypeError, event, 'some/event')


class TestEventProcessor(TestCase):
    def setUp(self):
        class A(EventProcessor):
            @event('some/event')
            def test1(self):
                return "Supercomplicated handling"
        self.a = A()

    def test_event_handler(self):
        self.assertEqual(self.a._get_event_handler( 'some/event').__name__, "test1")
        self.assertIsNone(self.a._get_event_handler('some/bullshit'))

    def test_math_event(self):
        self.assertTrue(self.a.match_event('some/event'))
        self.assertFalse(self.a.match_event('some/bullshit'))

    def test_event(self):
        self.assertEqual(self.a.event('some/event'), 'Supercomplicated handling')
        self.assertIsNone(self.a.event('some/bullshit'))


# (kudrom) TODO: We have to test the on_session_start callback in a integration test
class TestSessionPlugin(TestCase):
    pass
