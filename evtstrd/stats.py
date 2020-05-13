import datetime
from typing import Dict, Any, Iterable

from evtstrd.listener import Listener


class ServerStats:
    def __init__(self) -> None:
        self.start_time = datetime.datetime.now()
        self.total_connections = 0


def json_stats(
    stats: ServerStats, listeners: Iterable[Listener]
) -> Dict[str, Any]:
    def json_connection(listener: Listener) -> Dict[str, Any]:
        c = {
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
