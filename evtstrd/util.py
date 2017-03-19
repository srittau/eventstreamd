import asyncio
import json
import logging

from evtstrd.exc import DisconnectedError


@asyncio.coroutine
def read_json_line(reader):
    while True:
        line = yield from reader.readline()
        if line:
            try:
                return json.loads(line.decode("utf-8").strip())
            except (ValueError, UnicodeDecodeError):
                logging.warning("invalid JSON received")
        if reader.at_eof():
            raise DisconnectedError()
