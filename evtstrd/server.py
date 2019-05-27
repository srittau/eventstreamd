from __future__ import annotations

import asyncio
import asyncio.log
import signal
from asyncio import AbstractEventLoop
from collections import defaultdict
from typing import List, Dict

from evtstrd.config import Config
from evtstrd.http_server import HTTPServer
from evtstrd.listener import Listener
from evtstrd.socket_server import SocketServer


def run_server(config: Config) -> None:
    listeners: Dict[str, List[Listener]] = defaultdict(list)
    loop = asyncio.get_event_loop()
    _setup_signal_handlers(loop)
    with SocketServer(loop, config, listeners):
        with HTTPServer(loop, config, listeners):
            loop.run_forever()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


def _setup_signal_handlers(loop: AbstractEventLoop) -> None:
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
