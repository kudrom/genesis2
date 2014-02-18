from unittest import TestCase
from genesis2.webserver.root.xslt import *


class TestAttr(TestCase):
    def test_empty(self):
        ret = attr(None, [], "chosen")
        self.assertEqual(ret, "chosen")

    def test_none(self):
        ret = attr(None, ["None"], "chosen")
        self.assertEqual(ret, "chosen")

    def test_populated(self):
        ret = attr(None, ["chosen"], None)
        self.assertEqual(ret, "chosen")


class TestCss(TestCase):
    def test_auto_empty_none(self):
        ret = css(None, [], "auto")
        self.assertEqual(ret, "auto")

    def test_auto_list(self):
        ret = css(None, ["auto"], None)
        self.assertEqual(ret, "auto")

    def test_pixels(self):
        ret = css(None, ["10"], None)
        self.assertEqual(ret, "10px")

    def test_percent(self):
        ret = css(None, ["40%"], None)
        self.assertEqual(ret, "40%")


class TestIff(TestCase):
    def test_select_chosen(self):
        ret = iif(None, True, "chosen", "discarded")
        self.assertEqual(ret, "chosen")

    def test_select_discarded(self):
        ret = iif(None, False, "chosen", "discarded")
        self.assertEqual(ret, "discarded")

    def test_select_chosen_lowercase(self):
        ret = iif(None, ["True"], "chosen", "discarded")
        self.assertEqual(ret, "chosen")

    def test_select_discarded_lowercase(self):
        ret = iif(None, ["bullshit"], "chosen", "discarded")
        self.assertEqual(ret, "discarded")


# These are the same for idesc and b64
class Testjsesc(TestCase):
    def test_string(self):
        ret = jsesc(None, "replace'")
        self.assertEqual(ret, "replace\\")

    def test_list(self):
        ret = jsesc(None, ["replace'"])
        self.assertEqual(ret, "replace\\")
