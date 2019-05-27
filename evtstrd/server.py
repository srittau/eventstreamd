from __future__ import annotations

import signal
from asyncio import AbstractEventLoop, get_event_loop

from evtstrd.config import Config
from evtstrd.dispatcher import Dispatcher
from evtstrd.http_server import HTTPServer
from evtstrd.socket_server import SocketServer
from evtstrd.stats import ServerStats


def run_server(config: Config) -> None:
    loop = get_event_loop()
    _setup_signal_handlers(loop)
    stats = ServerStats()
    dispatcher = Dispatcher(loop, config, stats)
    with SocketServer(loop, config, dispatcher):
        with HTTPServer(loop, config, dispatcher, stats):
            loop.run_forever()
            dispatcher.disconnect_all()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


def _setup_signal_handlers(loop: AbstractEventLoop) -> None:
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
