import asyncio
import datetime
import itertools
import logging
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from typing import Sequence, Optional, Callable, Any, cast

from evtstrd.config import Config
from evtstrd.events import JSONEvent, PingEvent, Event
from evtstrd.exc import DisconnectedError
from evtstrd.filters import Filter
from evtstrd.http import write_chunk


class Listener:
    _id_counter = itertools.count(1)

    def __init__(
        self,
        config: Config,
        reader: StreamReader,
        writer: StreamWriter,
        subsystem: str,
        filters: Sequence[Filter],
        *,
        loop: AbstractEventLoop = None,
    ) -> None:
        self.id = next(self._id_counter)
        self._config = config
        self.loop = loop or asyncio.get_event_loop()
        self.subsystem = subsystem
        self.filters = filters
        self.reader = reader
        self.writer = writer
        self.on_close: Optional[Callable[[Listener], None]] = None
        self.connection_time = datetime.datetime.now()
        self.referer: Optional[str] = None

    def __str__(self) -> str:
        return f"#{self.id}"

    def __repr__(self) -> str:
        return "<Listener 0x{:x} for {}>".format(id(self), self.subsystem)

    @property
    def remote_host(self) -> Optional[str]:
        return cast(Optional[str], self.writer.get_extra_info("peername")[0])

    def notify(self, event_type: str, data: Any, id: str = None) -> None:
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
            await asyncio.sleep(self._config.ping_interval, loop=self.loop)

    def _write_event(self, event: Event) -> None:
        if self.reader.at_eof():
            if self.on_close:
                self.on_close(self)
            raise DisconnectedError()
        write_chunk(self.writer, bytes(event))

    def disconnect(self) -> None:
        self.writer.close()
