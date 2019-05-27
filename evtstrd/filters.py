import datetime
import re
from typing import Callable, Union, Type, Any, cast

from jsonget import json_get, JsonValue, JsonType

from evtstrd.date import parse_iso_date


_Comparator = Callable[[str, Any], bool]


class Filter:
    def __init__(
        self, field: str, comparator: _Comparator, value: Any, string: str
    ) -> None:
        self._field = field
        self._comparator = comparator
        self._value = value
        self.string = string

    def __call__(self, message: JsonValue) -> bool:
        try:
            v = self._get_value(message)
        except ValueError:
            return False
        return self._comparator(v, self._value)

    def __str__(self) -> str:
        return self.string

    def _get_value(self, message: JsonValue) -> Any:
        try:
            v = json_get(message, self._field, self.field_type)
        except (ValueError, TypeError):
            raise ValueError()
        return self.parse_value(cast(Any, v))

    @property
    def field_type(self) -> JsonType:
        raise NotImplementedError()

    def parse_value(self, v: str) -> Any:
        raise NotImplementedError()


class StringFilter(Filter):
    @property
    def field_type(self) -> JsonType:
        return type(self._value)

    def parse_value(self, v: str) -> str:
        return v


class DateFilter(Filter):
    @property
    def field_type(self) -> Type[str]:
        return str

    def parse_value(self, v: str) -> datetime.date:
        return parse_iso_date(v)


_filter_re = re.compile(r"^([a-z.-]+)(=|>=|<=|<|>)(.*)$")
_comparators = {
    "=": lambda v1, v2: v1 == v2,
    ">": lambda v1, v2: v1 > v2,
    ">=": lambda v1, v2: v1 >= v2,
    "<": lambda v1, v2: v1 < v2,
    "<=": lambda v1, v2: v1 <= v2,
}


def _parse_value(v: str) -> Union[str, int, datetime.date]:
    if len(v) >= 2 and v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    try:
        return parse_iso_date(v)
    except ValueError:
        pass
    return int(v)


def parse_filter(string: str) -> Filter:
    m = _filter_re.match(string)
    if not m:
        raise ValueError(f"invalid filter '{string}'")
    field = m.group(1).replace(".", "/")
    comparator = _comparators[m.group(2)]
    value = _parse_value(m.group(3))
    if type(value) == datetime.date:
        cls: Type[Filter] = DateFilter
    else:
        cls = StringFilter
    return cls(field, comparator, value, string)
