import asyncio
import datetime
import json
import logging
from asyncio.streams import StreamReader
from typing import Any

from evtstrd.exc import DisconnectedError


async def read_json_line(reader: StreamReader) -> Any:
    while True:
        line = await reader.readline()
        if line:
            logging.debug(f"read line from socket: {line!r}")
            try:
                return json.loads(line.decode("utf-8").strip())
            except (ValueError, UnicodeDecodeError):
                logging.warning("invalid JSON received")
        if reader.at_eof():
            raise DisconnectedError()


_RECHECK_SECONDS = 60  # in seconds


async def sleep_until(dt: datetime.datetime) -> None:
    while True:
        now = datetime.datetime.utcnow()
        if now >= dt:
            return
        remaining = (dt - now).total_seconds()
        await asyncio.sleep(min(remaining, _RECHECK_SECONDS))
