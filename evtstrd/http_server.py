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
from typing import List, Optional, Dict, Mapping, Tuple, Type
from urllib.parse import urlparse, ParseResult, parse_qs

from evtstrd.auth import check_auth
from evtstrd.config import Config
from evtstrd.dispatcher import Dispatcher
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
    write_response,
)
from evtstrd.stats import ServerStats, json_stats


class HTTPServer:
    def __init__(
        self,
        loop: AbstractEventLoop,
        config: Config,
        dispatcher: Dispatcher,
        stats: ServerStats,
    ) -> None:
        self._loop = loop
        self._config = config
        self._handler = HTTPHandler(config, dispatcher, stats, loop=loop)
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
    ) -> None:
        assert self._server is not None
        self._server.close()
        hs = self._server.wait_closed()
        self._loop.run_until_complete(asyncio.wait([hs], timeout=5))


class HTTPHandler:
    def __init__(
        self,
        config: Config,
        dispatcher: Dispatcher,
        stats: ServerStats,
        *,
        loop: AbstractEventLoop = None,
    ) -> None:
        self._config = config
        self._dispatcher = dispatcher
        self._stats = stats
        self._loop = loop or asyncio.get_event_loop()

    async def handle(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            method, path, headers = await read_http_head(reader)
            await self._handle_request(reader, writer, method, path, headers)
        except HTTPError as exc:
            write_http_error(writer, exc)
        except Exception as exc:
            logging.exception(exc)
            write_response(
                writer,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                [],
                "Internal Server Error\r\n",
            )
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
            await self._handle_get_stats(writer, headers)
        else:
            raise NotFoundError(path)

    def _default_headers(self) -> List[Header]:
        return [("Date", formatdate(usegmt=True)), ("Server", "eventstreamd")]

    async def _handle_get_events(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        url: ParseResult,
        headers: Mapping[str, str],
    ) -> None:
        subsystem, filters = self._parse_event_args(url.query)
        expire, data = await check_auth("events", headers, subsystem=subsystem)
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
        referer = headers.get("referer")
        await self._dispatcher.handle_listener(
            reader, writer, referer, subsystem, filters, expire=expire
        )

    def _parse_event_args(self, query: str) -> Tuple[str, List[Filter]]:
        args = parse_qs(query)
        if "subsystem" not in args:
            raise CGIArgumentError("subsystem", "missing argument")
        try:
            filters = [parse_filter(f) for f in args.get("filter", [])]
        except ValueError:
            raise CGIArgumentError("filter", "could not parse filter")
        return args["subsystem"][0], filters

    async def _handle_get_stats(
        self, writer: StreamWriter, headers: Mapping[str, str]
    ) -> None:
        await check_auth("stats", headers)
        j = json_stats(self._stats, self._dispatcher.all_listeners)
        response = json.dumps(j).encode("utf-8")
        response_headers = self._default_headers() + [
            ("Connection", "close"),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response))),
        ]
        write_http_head(writer, HTTPStatus.OK, response_headers)
        writer.write(response)
        writer.close()
