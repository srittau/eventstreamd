import datetime
from unittest import TestCase

from asserts import assert_equal, assert_raises_regex

from evtstrd.date import parse_iso_date


class ParseISODateTest(TestCase):
    def test_empty(self) -> None:
        with assert_raises_regex(ValueError, "invalid date ''"):
            parse_iso_date("")

    def test_invalid(self) -> None:
        with assert_raises_regex(ValueError, "invalid date 'INVALID'"):
            parse_iso_date("INVALID")

    def test_with_dashes(self) -> None:
        date = parse_iso_date("2015-04-13")
        assert_equal(datetime.date(2015, 4, 13), date)

    def test_without_dashes(self) -> None:
        date = parse_iso_date("20150413")
        assert_equal(datetime.date(2015, 4, 13), date)

    def test_out_of_range(self) -> None:
        with assert_raises_regex(ValueError, "invalid date '20151304'"):
            parse_iso_date("20151304")
