from unittest import TestCase
from mock import MagicMock
import gc

from genesis2.core.utils import Observable


class TestObservable(TestCase):
    def setUp(self):
        class Observable1(Observable):
            def important_method(self):
                self.notify_observers("message", "argument")

        class Observer(object):
            def __init__(self):
                self.messages = []

        self.observer = Observer
        self.observable = Observable1

    def test_add_observer(self):
        observable = self.observable()
        observer = self.observer()
        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 0)

        observer.notify = MagicMock()
        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)

    def test_notify(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()
        observable.add_observer(observer)

        observable.important_method()
        observer.notify.assert_called_once_with(observable, "message", "argument")

    def test_remove(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()

        ref = observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)
        observable.remove_observer(ref)
        self.assertEqual(observable.get_n_observers(), 0)

        # Just in case
        observable.remove_observer(ref)

    def test_weak(self):
        observable = self.observable()
        observer = self.observer()
        observer.notify = MagicMock()

        observable.add_observer(observer)
        self.assertEqual(observable.get_n_observers(), 1)

        del observer
        gc.collect()
        self.assertEqual(observable.get_n_observers(), 0)
