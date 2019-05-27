import asyncio
import datetime
import logging
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamWriter,
    FIRST_COMPLETED,
)
from collections import defaultdict
from typing import List, Dict, Optional, Sequence

from jsonget import JsonValue

from evtstrd.config import Config
from evtstrd.filters import Filter
from evtstrd.listener import Listener
from evtstrd.stats import ServerStats


class Dispatcher:
    def __init__(
        self, loop: AbstractEventLoop, config: Config, stats: ServerStats
    ) -> None:
        self._loop = loop
        self._config = config
        self._stats = stats
        self._listeners: Dict[str, List[Listener]] = defaultdict(list)

    @property
    def all_listeners(self) -> List[Listener]:
        all_listeners = []
        for key in self._listeners:
            all_listeners.extend(self._listeners[key])
        return all_listeners

    async def handle_listener(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        referer: Optional[str],
        subsystem: str,
        filters: Sequence[Filter],
        *,
        expire: Optional[datetime.datetime] = None,
    ) -> None:
        listener = self._setup_listener(
            reader, writer, referer, subsystem, filters
        )
        await self._run_listener(listener, expire)

    def _setup_listener(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        referer: Optional[str],
        subsystem: str,
        filters: Sequence[Filter],
    ) -> Listener:
        listener = Listener(
            self._config, reader, writer, subsystem, filters, loop=self._loop
        )
        listener.referer = referer
        listener.on_close = self._remove_listener
        self._listeners[subsystem].append(listener)
        self._stats.total_connections += 1
        self._log_listener_added(listener)
        return listener

    def _log_listener_added(self, listener: Listener) -> None:
        msg = (
            f"client {listener} subscribed to subsystem "
            f"'{listener.subsystem}'"
        )
        if listener.filters:
            filter_str = ", ".join(str(f) for f in listener.filters)
            msg += f" with filters {filter_str}"
        logging.info(msg)

    def _remove_listener(self, listener: Listener) -> None:
        self._listeners[listener.subsystem].remove(listener)
        logging.info(
            f"client {listener} disconnected from subsystem "
            f"'{listener.subsystem}'"
        )

    async def _run_listener(
        self, listener: Listener, expire: Optional[datetime.datetime]
    ) -> None:
        futures = [asyncio.ensure_future(listener.ping_loop())]
        if expire:
            futures.append(asyncio.ensure_future(listener.logout_at(expire)))
        await asyncio.wait(futures, return_when=FIRST_COMPLETED)
        for f in futures:
            f.cancel()

        listener.disconnect()

    def notify(
        self, subsystem: str, event_type: str, data: JsonValue, id: str
    ) -> None:
        # Copy the list of listeners, because it can be modified during the
        # iteration.
        listeners = self._listeners[subsystem][:]
        for listener in listeners:
            listener.notify(event_type, data, id)
        logging.info(
            f"notified {len(listeners)} listeners about '{event_type}' event "
            f"in subsystem '{subsystem}'"
        )

    def disconnect_all(self) -> None:
        for listener in self.all_listeners:
            listener.disconnect()
