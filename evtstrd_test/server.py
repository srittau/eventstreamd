from unittest.case import TestCase

from asserts import assert_true, assert_false, assert_raises

from evtstrd.server import parse_filter


class ParseFilterTest(TestCase):

    def test_invalid_filter(self):
        with assert_raises(ValueError):
            parse_filter("INVALID")

    def test_invalid_values(self):
        with assert_raises(ValueError):
            parse_filter("foo=bar")
        with assert_raises(ValueError):
            parse_filter("foo='bar")
        with assert_raises(ValueError):
            parse_filter("foo='")
        with assert_raises(ValueError):
            parse_filter("foo=2000-12-32")

    def test_no_such_field(self):
        f = parse_filter("foo<=10")
        assert_false(f({}))

    def test_wrong_type(self):
        f = parse_filter("foo<=10")
        assert_false(f({"foo": ""}))

    def test_eq_int(self):
        f = parse_filter("foo=10")
        assert_false(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_false(f({"foo": 11}))

    def test_le_int(self):
        f = parse_filter("foo<=10")
        assert_true(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_false(f({"foo": 11}))

    def test_ge_int(self):
        f = parse_filter("foo>=10")
        assert_false(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_true(f({"foo": 11}))

    def test_eq_str(self):
        f = parse_filter("foo='bar'")
        assert_false(f({"foo": "baz"}))
        assert_true(f({"foo": "bar"}))

    def test_eq_date(self):
        f = parse_filter("foo=2016-03-24")
        assert_false(f({"foo": "2000-01-01"}))
        assert_true(f({"foo": "2016-03-24"}))

    def test_nested_value(self):
        f = parse_filter("foo.bar<=10")
        assert_true(f({"foo": {"bar": 10}}))
