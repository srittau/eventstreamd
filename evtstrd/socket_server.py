from __future__ import annotations

import logging
import os
from asyncio import (
    AbstractServer,
    StreamReader,
    StreamWriter,
    open_unix_connection,
    start_unix_server,
)
from collections.abc import Coroutine
from grp import getgrnam
from pwd import getpwnam
from typing import Any

from jsonget import JsonValue, json_get

from evtstrd.config import Config
from evtstrd.dispatcher import Dispatcher
from evtstrd.exc import DisconnectedError, ServerAlreadyRunningError
from evtstrd.util import read_json_line


class SocketServer:
    def __init__(self, config: Config, dispatcher: Dispatcher) -> None:
        self._config = config
        self._filename = config.socket_file
        self._socket_handler = SocketHandler(dispatcher)
        self._server: AbstractServer | None = None

    async def __aenter__(self) -> None:
        await self._remove_stale_socket()
        self._server = await start_unix_server(
            self._socket_handler.handle, path=self._filename
        )
        self._change_socket_permissions()

    async def __aexit__(self, *_: object) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()
        try:
            os.remove(self._filename)
        except FileNotFoundError:
            pass

    async def _remove_stale_socket(self) -> None:
        if not os.path.exists(self._filename):
            return
        try:
            await open_unix_connection(self._filename)
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
    def __init__(self, dispatcher: Dispatcher) -> None:
        self._dispatcher = dispatcher

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
    def _get_event_data(message: JsonValue) -> tuple[str, str, JsonValue, str]:
        try:
            subsystem = json_get(message, "subsystem", str)
            event = json_get(message, "event", str)
            data = json_get(message, "data", dict)
            id = json_get(message, "id", str)
        except (ValueError, TypeError) as exc:
            logging.error("received invalid JSON: " + str(exc))
            raise ValueError(str(exc)) from exc
        return subsystem, event, data, id
