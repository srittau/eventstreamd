from __future__ import annotations

import asyncio
import datetime
import itertools
import logging
from asyncio import StreamReader, StreamWriter
from collections.abc import Callable, Iterable

from jsonget import JsonValue

from evtstrd.config import Config
from evtstrd.events import Event, JSONEvent, LogoutEvent, PingEvent
from evtstrd.exc import DisconnectedError
from evtstrd.filters import Filter
from evtstrd.http import write_chunk, write_last_chunk
from evtstrd.util import sleep_until


class Listener:
    _id_counter = itertools.count(1)

    def __init__(
        self,
        config: Config,
        reader: StreamReader,
        writer: StreamWriter,
        subsystem: str,
        filters: Iterable[Filter],
    ) -> None:
        self.id = next(self._id_counter)
        self._config = config
        self.subsystem = subsystem
        self.filters = filters
        self.reader = reader
        self.writer = writer
        self.on_close: Callable[[Listener], None] | None = None
        self.connection_time = datetime.datetime.now()
        self.referer: str | None = None

    def __str__(self) -> str:
        return f"#{self.id}"

    def __repr__(self) -> str:
        return "<Listener 0x{:x} for {}>".format(id(self), self.subsystem)

    @property
    def remote_host(self) -> str | None:
        host = self.writer.get_extra_info("peername")[0]
        if host is not None and not isinstance(host, str):
            raise RuntimeError(
                f"unexpected type of peername host {type(host)}"
            )
        return host

    def notify(
        self,
        event_type: str,
        data: JsonValue,
        id: str | None = None,
    ) -> None:
        if all(f(data) for f in self.filters):
            logging.debug(f"notifying client {self}")
            event = JSONEvent(event_type, data, id)
            try:
                self._write_event(event)
            except DisconnectedError:
                pass
        else:
            logging.debug(f"notifying client {self}: not all filters matched")

    async def ping_loop(self) -> None:
        while True:
            try:
                self._write_event(PingEvent())
            except DisconnectedError:
                break
            await asyncio.sleep(self._config.ping_interval)

    async def logout_at(self, time: datetime.datetime) -> None:
        await sleep_until(time)
        self._write_event(LogoutEvent())
        if self.on_close:
            self.on_close(self)

    def _write_event(self, event: Event) -> None:
        if self.reader.at_eof():
            if self.on_close:
                self.on_close(self)
            raise DisconnectedError()
        write_chunk(self.writer, bytes(event))

    def disconnect(self) -> None:
        write_last_chunk(self.writer)
        self.writer.close()
