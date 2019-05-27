from unittest import TestCase

from asserts import assert_true, assert_false, assert_equal, assert_raises

from evtstrd.filters import parse_filter


class FilterTest(TestCase):
    def test_str(self) -> None:
        filter_ = parse_filter("foo.bar<='ABC'")
        assert_equal("foo.bar<='ABC'", str(filter_))

    def test_string_filter__path_not_found(self) -> None:
        filter_ = parse_filter("foo.bar<='ABC'")
        assert_false(filter_({"foo": {}}))

    def test_string_filter__wrong_type(self) -> None:
        filter_ = parse_filter("foo.bar<='50'")
        assert_false(filter_({"foo": {"bar": 13}}))

    def test_string_filter__compare(self) -> None:
        filter_ = parse_filter("foo.bar<='ABC'")
        assert_true(filter_({"foo": {"bar": "AAA"}}))
        assert_true(filter_({"foo": {"bar": "ABC"}}))
        assert_false(filter_({"foo": {"bar": "CAA"}}))

    def test_string_filter__lt(self) -> None:
        filter_ = parse_filter("foo.bar<'ABC'")
        assert_true(filter_({"foo": {"bar": "AAA"}}))
        assert_false(filter_({"foo": {"bar": "ABC"}}))
        assert_false(filter_({"foo": {"bar": "CAA"}}))

    def test_string_filter__gt(self) -> None:
        filter_ = parse_filter("foo.bar>'ABC'")
        assert_false(filter_({"foo": {"bar": "AAA"}}))
        assert_false(filter_({"foo": {"bar": "ABC"}}))
        assert_true(filter_({"foo": {"bar": "CAA"}}))


class ParseFilterTest(TestCase):
    def test_invalid_filter(self) -> None:
        with assert_raises(ValueError):
            parse_filter("INVALID")

    def test_invalid_values(self) -> None:
        with assert_raises(ValueError):
            parse_filter("foo=bar")
        with assert_raises(ValueError):
            parse_filter("foo='bar")
        with assert_raises(ValueError):
            parse_filter("foo='")
        with assert_raises(ValueError):
            parse_filter("foo=2000-12-32")

    def test_no_such_field(self) -> None:
        f = parse_filter("foo<=10")
        assert_false(f({}))

    def test_wrong_type(self) -> None:
        f = parse_filter("foo<=10")
        assert_false(f({"foo": ""}))

    def test_eq_int(self) -> None:
        f = parse_filter("foo=10")
        assert_false(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_false(f({"foo": 11}))

    def test_le_int(self) -> None:
        f = parse_filter("foo<=10")
        assert_true(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_false(f({"foo": 11}))

    def test_ge_int(self) -> None:
        f = parse_filter("foo>=10")
        assert_false(f({"foo": 9}))
        assert_true(f({"foo": 10}))
        assert_true(f({"foo": 11}))

    def test_eq_str(self) -> None:
        f = parse_filter("foo='bar'")
        assert_false(f({"foo": "baz"}))
        assert_true(f({"foo": "bar"}))

    def test_eq_date(self) -> None:
        f = parse_filter("foo=2016-03-24")
        assert_false(f({"foo": "2000-01-01"}))
        assert_true(f({"foo": "2016-03-24"}))

    def test_nested_value(self) -> None:
        f = parse_filter("foo.bar<=10")
        assert_true(f({"foo": {"bar": 10}}))
