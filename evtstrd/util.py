import json
import logging
from asyncio.streams import StreamReader
from typing import Any

from evtstrd.exc import DisconnectedError


async def read_json_line(reader: StreamReader) -> Any:
    while True:
        line = await reader.readline()
        if line:
            try:
                return json.loads(line.decode("utf-8").strip())
            except (ValueError, UnicodeDecodeError):
                logging.warning("invalid JSON received")
        if reader.at_eof():
            raise DisconnectedError()
