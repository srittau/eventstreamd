from unittest import TestCase

from asserts import assert_true, assert_false, assert_equal

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
