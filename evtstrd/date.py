import datetime
import re


_iso_date_re = re.compile(r"^(\d\d\d\d)-?(\d\d)-?(\d\d)$")


def parse_iso_date(date_string):
    if not date_string:
        raise ValueError(f"invalid date '{date_string}'")
    m = _iso_date_re.match(date_string)
    if not m:
        raise ValueError(f"invalid date '{date_string}'")
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError as exc:
        raise ValueError(f"invalid date '{date_string}'") from exc
