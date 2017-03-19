import datetime
from unittest.case import TestCase

from asserts import assert_raises, assert_equal, assert_raises_regex

from evtstrd.date import parse_iso_date


class ParseISODateTest(TestCase):

    def test_empty(self):
        with assert_raises_regex(ValueError, "invalid date ''"):
            parse_iso_date("")

    def test_invalid(self):
        with assert_raises_regex(ValueError, "invalid date 'INVALID'"):
            parse_iso_date("INVALID")

    def test_with_dashes(self):
        date = parse_iso_date("2015-04-13")
        assert_equal(datetime.date(2015, 4, 13), date)

    def test_without_dashes(self):
        date = parse_iso_date("20150413")
        assert_equal(datetime.date(2015, 4, 13), date)

    def test_out_of_range(self):
        with assert_raises_regex(ValueError, "invalid date '20151304'"):
            parse_iso_date("20151304")
