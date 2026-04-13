import datetime
from collections.abc import Iterable
from typing import NotRequired, TypedDict

from evtstrd.listener import Listener

JSONConnection = TypedDict(
    "JSONConnection",
    {
        "subsystem": str,
        "filters": list[str],
        "connection-time": str,
        "remote-host": str | None,
        "referer": NotRequired[str],
    },
)

JSONStats = TypedDict(
    "JSONStats",
    {
        "start-time": str,
        "total-connections": int,
        "connections": list[JSONConnection],
    },
)


class ServerStats:
    def __init__(self) -> None:
        self.start_time = datetime.datetime.now()
        self.total_connections = 0


def json_stats(stats: ServerStats, listeners: Iterable[Listener]) -> JSONStats:
    def json_connection(listener: Listener) -> JSONConnection:
        c: JSONConnection = {
            "subsystem": listener.subsystem,
            "filters": [str(f) for f in listener.filters],
            "connection-time": listener.connection_time.isoformat(),
            "remote-host": listener.remote_host,
        }
        if listener.referer:
            c["referer"] = listener.referer
        return c

    return {
        "start-time": stats.start_time.isoformat(),
        "total-connections": stats.total_connections,
        "connections": [json_connection(li) for li in listeners],
    }
