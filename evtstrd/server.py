from __future__ import annotations

import asyncio
import signal
from asyncio import get_event_loop

from evtstrd.config import Config
from evtstrd.dispatcher import Dispatcher
from evtstrd.http_server import HTTPServer
from evtstrd.socket_server import SocketServer
from evtstrd.stats import ServerStats


async def run_server(config: Config) -> None:
    stop_event = asyncio.Event()
    _setup_signal_handlers(stop_event)

    stats = ServerStats()
    dispatcher = Dispatcher(config, stats)
    async with SocketServer(config, dispatcher):
        async with HTTPServer(config, dispatcher, stats):
            await stop_event.wait()
            dispatcher.disconnect_all()


def _setup_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = get_event_loop()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
