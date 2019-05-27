import json
from typing import Any, SupportsBytes


class Event(SupportsBytes):

    """A single event stream event.

    Each event has a type (this is not actually required by the event stream
    protocol) and data. It can optionally have an id. Use of ids is recommended
    to allow safe stream reconnections.
    """

    def __init__(
        self, event_type: str, data: str = "", id: str = None
    ) -> None:
        self.type = event_type
        self.id = id
        self.data = data

    def __bytes__(self) -> bytes:
        """Serialize the event for use in event streams."""
        return bytes(str(self), "utf-8")

    def __str__(self) -> str:
        """Serialize the event for use in event streams."""
        fields = [("event", self.type), ("data", self.data)]
        if self.id:
            fields.append(("id", self.id))
        lines = ["{}: {}".format(f[0], f[1]) for f in fields]
        return "\r\n".join(lines) + "\r\n\r\n"


class PingEvent(Event):
    def __init__(self) -> None:
        super().__init__("ping")


class JSONEvent(Event):
    def __init__(
        self, event_type: str, json_data: Any, id: str = None
    ) -> None:
        if not isinstance(json_data, str):
            json_data = json.dumps(json_data)
        super().__init__(event_type, json_data, id)


class LogoutEvent(JSONEvent):
    def __init__(self) -> None:
        super().__init__("logout", {"reason": "expire"})
