from __future__ import annotations

import asyncio
import json
import logging
import ssl
from asyncio import (
    AbstractEventLoop,
    AbstractServer,
    StreamReader,
    StreamWriter,
)
from email.utils import formatdate
from http import HTTPStatus
from ssl import SSLContext
from types import TracebackType
from typing import (
    MutableMapping,
    List,
    Optional,
    Dict,
    Sequence,
    Mapping,
    Tuple,
    Type,
)
from urllib.parse import urlparse, ParseResult, parse_qs

from evtstrd.config import Config
from evtstrd.filters import Filter, parse_filter
from evtstrd.http import (
    read_http_head,
    HTTPError,
    write_http_error,
    MethodNotAllowedError,
    NotFoundError,
    Header,
    write_http_head,
    CGIArgumentError,
)
from evtstrd.listener import Listener
from evtstrd.stats import ServerStats, json_stats


class HTTPServer:
    def __init__(
        self,
        loop: AbstractEventLoop,
        config: Config,
        listeners: MutableMapping[str, List[Listener]],
    ) -> None:
        self._loop = loop
        self._config = config
        self._handler = HTTPHandler(config, listeners, loop=loop)
        self._server: Optional[AbstractServer] = None

    def __enter__(self) -> None:
        ssl_context = self._ssl_context()
        f = asyncio.start_server(
            self._handler.handle, port=self._config.http_port, ssl=ssl_context
        )
        self._server = self._loop.run_until_complete(f)

    def _ssl_context(self) -> Optional[SSLContext]:
        if not self._config.with_ssl:
            return None
        assert self._config.cert_file is not None
        assert self._config.key_file is not None
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(self._config.cert_file, self._config.key_file)
        return ctx

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> bool:
        assert self._server is not None
        self._server.close()
        hs = self._server.wait_closed()
        self._loop.run_until_complete(asyncio.wait([hs], timeout=5))
        self._handler.disconnect_all()
        return False


class HTTPHandler:
    def __init__(
        self,
        config: Config,
        listeners: MutableMapping[str, List[Listener]],
        *,
        loop: AbstractEventLoop = None,
    ) -> None:
        self._config = config
        self._listeners = listeners
        self._stats = ServerStats()
        self._loop = loop or asyncio.get_event_loop()

    async def handle(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            method, path, headers = await read_http_head(reader)
            await self._handle_request(reader, writer, method, path, headers)
        except HTTPError as exc:
            write_http_error(writer, exc)
        writer.close()

    async def _handle_request(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        method: str,
        path: str,
        headers: Dict[str, str],
    ) -> None:
        url = urlparse(path)
        if url.path == "/events":
            if method != "GET":
                raise MethodNotAllowedError(method)
            await self._handle_get_events(reader, writer, url, headers)
        elif url.path == "/stats":
            if method != "GET":
                raise MethodNotAllowedError(method)
            self._handle_get_stats(writer)
        else:
            raise NotFoundError(path)

    def _default_headers(self) -> List[Header]:
        return [("Date", formatdate(usegmt=True)), ("Server", "eventstreamd")]

    async def _handle_get_events(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        url: ParseResult,
        headers: Dict[str, str],
    ) -> None:
        subsystem, filters = self._parse_event_args(url.query)
        response_headers = self._default_headers() + [
            ("Transfer-Encoding", "chunked"),
            ("Content-Type", "text/event-stream"),
            ("Connection", "keep-alive"),
            ("Keep-Alive", "timeout=5, max=100"),
        ]
        if "origin" in headers:
            response_headers.extend(
                [
                    ("Access-Control-Allow-Credentials", "true"),
                    ("Access-Control-Allow-Origin", headers["origin"]),
                ]
            )
        write_http_head(writer, HTTPStatus.OK, response_headers)
        await self._setup_listener(reader, writer, headers, subsystem, filters)

    async def _setup_listener(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        headers: Dict[str, str],
        subsystem: str,
        filters: Sequence[Filter],
    ) -> None:
        listener = self._create_listener(
            reader, writer, headers, subsystem, filters
        )
        self._listeners[subsystem].append(listener)
        self._stats.total_connections += 1
        await listener.ping_loop()

    def _create_listener(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        headers: Mapping[str, str],
        subsystem: str,
        filters: Sequence[Filter],
    ) -> Listener:
        listener = Listener(
            self._config, reader, writer, subsystem, filters, loop=self._loop
        )
        listener.on_close = self._remove_listener
        listener.remote_host = writer.get_extra_info("peername")[0]
        listener.referer = headers.get("referer")
        self._log_listener_created(listener)
        return listener

    def _log_listener_created(self, listener: Listener) -> None:
        msg = (
            f"client {listener} subscribed to subsystem "
            f"'{listener.subsystem}'"
        )
        if listener.filters:
            filter_str = ", ".join(str(f) for f in listener.filters)
            msg += f" with filters {filter_str}"
        logging.info(msg)

    def _remove_listener(self, listener: Listener) -> None:
        logging.info(
            f"client {listener} disconnected from subsystem "
            f"'{listener.subsystem}'"
        )
        self._listeners[listener.subsystem].remove(listener)

    def _parse_event_args(self, query: str) -> Tuple[str, List[Filter]]:
        args = parse_qs(query)
        if "subsystem" not in args:
            raise CGIArgumentError("subsystem", "missing argument")
        try:
            filters = [parse_filter(f) for f in args.get("filter", [])]
        except ValueError:
            raise CGIArgumentError("filter", "could not parse filter")
        return args["subsystem"][0], filters

    @property
    def _all_listeners(self) -> List[Listener]:
        all_listeners = []
        for key in self._listeners:
            all_listeners.extend(self._listeners[key])
        return all_listeners

    def _handle_get_stats(self, writer: StreamWriter) -> None:
        j = json_stats(self._stats, self._all_listeners)
        response = json.dumps(j).encode("utf-8")
        response_headers = self._default_headers() + [
            ("Connection", "close"),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response))),
        ]
        write_http_head(writer, HTTPStatus.OK, response_headers)
        writer.write(response)
        writer.close()

    def disconnect_all(self) -> None:
        for listener in self._all_listeners:
            listener.disconnect()
