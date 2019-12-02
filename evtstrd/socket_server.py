from __future__ import annotations

import logging
import os
from asyncio import (
    AbstractEventLoop,
    AbstractServer,
    StreamReader,
    StreamWriter,
    get_event_loop,
    start_unix_server,
    open_unix_connection,
    wait,
)
from grp import getgrnam
from pwd import getpwnam
from types import TracebackType
from typing import Any, Coroutine, Type, Optional, Tuple

from jsonget import json_get, JsonValue

from evtstrd.config import Config
from evtstrd.dispatcher import Dispatcher
from evtstrd.exc import ServerAlreadyRunningError, DisconnectedError
from evtstrd.util import read_json_line


class SocketServer:
    def __init__(
        self, loop: AbstractEventLoop, config: Config, dispatcher: Dispatcher
    ) -> None:
        self._loop = loop
        self._config = config
        self._filename = config.socket_file
        self._socket_handler = SocketHandler(dispatcher, loop=loop)
        self._server: Optional[AbstractServer] = None

    def __enter__(self) -> None:
        self._remove_stale_socket()
        f = start_unix_server(self._socket_handler.handle, path=self._filename)
        self._server = self._loop.run_until_complete(f)
        self._change_socket_permissions()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        assert self._server is not None
        self._server.close()
        wc = self._server.wait_closed()
        self._loop.run_until_complete(wait([wc], timeout=5))
        try:
            os.remove(self._filename)
        except FileNotFoundError:
            pass

    def _remove_stale_socket(self) -> None:
        if not os.path.exists(self._filename):
            return
        try:
            fut = open_unix_connection(self._filename)
            self._loop.run_until_complete(fut)
        except ConnectionRefusedError:
            os.remove(self._filename)
            logging.warning(f"removed stale socket file {self._filename}")
        else:
            raise ServerAlreadyRunningError()

    def _change_socket_permissions(self) -> None:
        os.chmod(self._filename, self._config.socket_mode)
        if not self._config.socket_owner:
            new_owner = -1
        else:
            new_owner = getpwnam(self._config.socket_owner).pw_uid
        if not self._config.socket_group:
            new_group = -1
        else:
            new_group = getgrnam(self._config.socket_group).gr_gid
        if new_owner != -1 or new_group != -1:
            os.chown(self._filename, new_owner, new_group)

    def close(self) -> Coroutine[Any, Any, None]:
        assert self._server is not None
        self._server.close()
        return self._server.wait_closed()


class SocketHandler:
    def __init__(
        self, dispatcher: Dispatcher, *, loop: AbstractEventLoop = None
    ) -> None:
        self._dispatcher = dispatcher
        self._loop = loop or get_event_loop()

    async def handle(self, reader: StreamReader, _: StreamWriter) -> None:
        while True:
            try:
                message = await read_json_line(reader)
            except DisconnectedError:
                break
            action = json_get(message, "action", str)
            if action == "notify":
                self._notify_dispatcher(message)
            else:
                logging.warning(f"received unknown action '{action}'")

    def _notify_dispatcher(self, message: JsonValue) -> None:
        try:
            subsystem, event, data, id = self._get_event_data(message)
        except ValueError:
            pass
        else:
            self._dispatcher.notify(subsystem, event, data, id)

    @staticmethod
    def _get_event_data(message: JsonValue) -> Tuple[str, str, JsonValue, str]:
        try:
            subsystem = json_get(message, "subsystem", str)
            event = json_get(message, "event", str)
            data = json_get(message, "data", dict)
            id = json_get(message, "id", str)
        except (ValueError, TypeError) as exc:
            logging.error("received invalid JSON: " + str(exc))
            raise ValueError()
        return subsystem, event, data, id
