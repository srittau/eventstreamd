from unittest import TestCase

from asserts import assert_equal

from evtstrd.events import Event, JSONEvent


class EventTest(TestCase):
    def test_str(self) -> None:
        event = Event("add", "test-data")
        string = str(event)
        assert_equal("event: add\r\ndata: test-data\r\n\r\n", string)


class JSONEventTest(TestCase):
    def test_exercise(self) -> None:
        JSONEvent("add", {})
