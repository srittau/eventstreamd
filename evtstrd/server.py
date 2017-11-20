import asyncio
import asyncio.log
import datetime
import json
import re
import signal
import ssl
import logging
import os
import sys
from asyncio.events import AbstractEventLoop
from asyncio.streams import StreamReader, StreamWriter
from collections import defaultdict
from email.utils import formatdate
from grp import getgrnam
from http import HTTPStatus
from pwd import getpwnam
from ssl import SSLContext
from typing import \
    List, Dict, Any, Sequence, Callable, Union, Type, Tuple, \
    Mapping, Optional
from urllib.parse import urlparse, parse_qs, ParseResult

from jsonget import json_get, JsonType, JsonValue

from evtstrd.cmdargs import parse_command_line
from evtstrd.config import Config
from evtstrd.date import parse_iso_date
from evtstrd.events import JSONEvent, PingEvent, Event
from evtstrd.exc import DisconnectedError
from evtstrd.http import \
    HTTPError, CGIArgumentError, NotFoundError, MethodNotAllowedError, \
    read_http_head, write_http_error, write_http_head, write_chunk, Header
from evtstrd.util import read_json_line


_Comparator = Callable[[str, Any], bool]


def run_notification_server() -> None:
    config = parse_command_line()
    logging.getLogger("asyncio").disabled = not config.debug
    if config.debug:
        logging.root.setLevel(logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.DEBUG)
    NotificationServer(config).run()


class NotificationServer:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._http_server = None
        self._socket_server = None
        self._loop = asyncio.get_event_loop()
        self._listeners: Dict[str, List[Listener]] = defaultdict(list)
        self._stats = ServerStats()
        self._socket_handler = SocketHandler(self._listeners, loop=self._loop)
        self._http_handler = HTTPHandler(
            config, self._listeners, self._stats, loop=self._loop)
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        self._loop.add_signal_handler(signal.SIGINT, self._loop.stop)
        self._loop.add_signal_handler(signal.SIGTERM, self._loop.stop)

    def run(self) -> None:
        self._remove_stale_socket()
        try:
            self._run_loop()
        finally:
            try:
                os.remove(self._config.socket_file)
            except FileNotFoundError:
                pass

    def _remove_stale_socket(self) -> None:
        if not os.path.exists(self._config.socket_file):
            return
        try:
            fut = asyncio.open_unix_connection(self._config.socket_file)
            self._loop.run_until_complete(fut)
        except ConnectionRefusedError:
            os.remove(self._config.socket_file)
            logging.warning("removed stale socket file {}".format(
                self._config.socket_file))
        else:
            print("server already running, exiting", file=sys.stderr)
            sys.exit(1)

    def _run_loop(self) -> None:
        self._start_socket()
        self._start_http_server()
        self._change_socket_permissions()
        self._loop.run_forever()
        self._shutdown()

    def _shutdown(self) -> None:
        fs: List[Any] = []
        if self._http_server:
            self._http_server.close()
            fs.append(self._http_server.wait_closed())
        if self._socket_server:
            self._socket_server.close()
            fs.append(self._socket_server.wait_closed())
        self._loop.run_until_complete(asyncio.wait(fs, timeout=5))
        self._http_handler.disconnect_all()
        self._loop.shutdown_asyncgens()

    def _start_socket(self) -> None:
        f = asyncio.start_unix_server(
            self._socket_handler.handle, path=self._config.socket_file)
        self._socket_server = self._loop.run_until_complete(f)

    def _start_http_server(self) -> None:
        if self._config.with_ssl:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            assert self._config.cert_file is not None
            assert self._config.key_file is not None
            ctx.load_cert_chain(
                self._config.cert_file, self._config.key_file)
            ssl_context: Optional[SSLContext] = ctx
        else:
            ssl_context = None
        f = asyncio.start_server(
            self._http_handler.handle, port=self._config.http_port,
            ssl=ssl_context)
        self._http_server = self._loop.run_until_complete(f)

    def _change_socket_permissions(self) -> None:
        os.chmod(self._config.socket_file, self._config.socket_mode)
        if not self._config.socket_owner:
            new_owner = -1
        else:
            new_owner = getpwnam(self._config.socket_owner).pw_uid
        if not self._config.socket_group:
            new_group = -1
        else:
            new_group = getgrnam(self._config.socket_group).gr_gid
        if new_owner != -1 or new_group != -1:
            os.chown(self._config.socket_file, new_owner, new_group)


class SocketHandler:

    def __init__(self, listeners: Dict[str, List["Listener"]], *,
                 loop: AbstractEventLoop = None) \
            -> None:
        self._listeners = listeners
        self._loop = loop or asyncio.get_event_loop()

    async def handle(self, reader: StreamReader, _: StreamWriter) -> None:
        while True:
            try:
                message = await read_json_line(reader)
            except DisconnectedError:
                break
            action = json_get(message, "action", str)
            logging.debug("received a '{}' message".format(action))
            if action == "notify":
                self._notify_listeners_about_message(message)
            else:
                logging.warning("received unknown action '{}'".format(action))

    def _notify_listeners_about_message(self, message: JsonValue) -> None:
        try:
            subsystem, event, data, id = self._get_event_data(message)
        except ValueError:
            pass
        else:
            self._notify_listeners(subsystem, event, data, id)

    def _notify_listeners(self, subsystem: str, event_type: str,
                          data: JsonValue, id: str) -> None:
        listeners = self._listeners[subsystem]
        # Copy the list of listeners, because it can be modified during the
        # iteration.
        for listener in listeners[:]:
            listener.notify(event_type, data, id)
        logging.info(
            "notified {} listeners about {} event in subsystem '{}'".format(
                len(listeners), event_type, subsystem))

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


class HTTPHandler:

    def __init__(self, config: Config, listeners: Dict[str, List["Listener"]],
                 stats: "ServerStats", *, loop: AbstractEventLoop = None) \
            -> None:
        self._config = config
        self._listeners = listeners
        self._stats = stats
        self._loop = loop or asyncio.get_event_loop()

    async def handle(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            method, path, headers = await read_http_head(reader)
            await self._handle_request(
                reader, writer, method, path, headers)
        except HTTPError as exc:
            write_http_error(writer, exc)
        writer.close()

    async def _handle_request(
            self, reader: StreamReader, writer: StreamWriter,
            method: str, path: str, headers: Dict[str, str]) \
            -> None:
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
        return [
            ("Date", formatdate(usegmt=True)),
            ("Server", "zzb-notificationd"),
        ]

    async def _handle_get_events(
            self, reader: StreamReader, writer: StreamWriter,
            url: ParseResult, headers: Dict[str, str]) -> None:
        subsystem, filters = self._parse_event_args(url.query)
        response_headers = self._default_headers() + [
            ("Transfer-Encoding", "chunked"),
            ("Content-Type", "text/event-stream"),
            ("Connection", "keep-alive"),
            ("Keep-Alive", "timeout=5, max=100"),
        ]
        if "origin" in headers:
            response_headers.extend([
                ("Access-Control-Allow-Credentials", "true"),
                ("Access-Control-Allow-Origin", headers["origin"]),
            ])
        write_http_head(writer, HTTPStatus.OK, response_headers)
        await self._setup_listener(
            reader, writer, headers, subsystem, filters)

    async def _setup_listener(
            self, reader: StreamReader, writer: StreamWriter,
            headers: Dict[str, str], subsystem: str,
            filters: Sequence["Filter"]) -> None:
        listener = self._create_listener(
            reader, writer, headers, subsystem, filters)
        self._listeners[subsystem].append(listener)
        self._stats.total_connections += 1
        await listener.ping_loop()

    def _create_listener(self, reader: StreamReader, writer: StreamWriter,
                         headers: Mapping[str, str], subsystem: str,
                         filters: Sequence["Filter"]) -> "Listener":
        logging.info("client subscribed to subsystem '{}'".format(subsystem))
        listener = Listener(
            self._config, reader, writer, subsystem, filters, loop=self._loop)
        listener.on_close = self._remove_listener
        listener.remote_host = writer.get_extra_info("peername")[0]
        listener.referer = headers.get("referer")
        return listener

    def _remove_listener(self, listener: "Listener") -> None:
        logging.info(
            "client disconnected from subsystem '{}'".format(
                listener.subsystem))
        self._listeners[listener.subsystem].remove(listener)

    def _parse_event_args(self, query: str) -> Tuple[str, List["Filter"]]:
        args = parse_qs(query)
        if "subsystem" not in args:
            raise CGIArgumentError("subsystem", "missing argument")
        try:
            filters = [parse_filter(f) for f in args.get("filter", [])]
        except ValueError:
            raise CGIArgumentError("filter", "could not parse filter")
        return args["subsystem"][0], filters

    @property
    def _all_listeners(self) -> List["Listener"]:
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
            ("Content-Length", str(len(response)))
        ]
        write_http_head(writer, HTTPStatus.OK, response_headers)
        writer.write(response)
        writer.close()

    def disconnect_all(self) -> None:
        for listener in self._all_listeners:
            listener.disconnect()


class Listener:

    def __init__(
            self, config: Config, reader: StreamReader, writer: StreamWriter,
            subsystem: str, filters: Sequence["Filter"],
            *, loop: AbstractEventLoop = None) -> None:
        self._config = config
        self.loop = loop or asyncio.get_event_loop()
        self.subsystem = subsystem
        self.filters = filters
        self.reader = reader
        self.writer = writer
        self.on_close: Optional[Callable[[Listener], None]] = None
        self.connection_time = datetime.datetime.now()
        self.remote_host: Optional[str] = None
        self.referer: Optional[str] = None

    def __repr__(self) -> str:
        return "<Listener 0x{:x} for {}>".format(id(self), self.subsystem)

    def notify(self, event_type: str, data: Any, id: str = None) -> None:
        if all(f(data) for f in self.filters):
            event = JSONEvent(event_type, data, id)
            try:
                self._write_event(event)
            except DisconnectedError:
                pass

    async def ping_loop(self) -> None:
        while True:
            try:
                self._write_event(PingEvent())
            except DisconnectedError:
                break
            await asyncio.sleep(
                self._config.ping_interval, loop=self.loop)

    def _write_event(self, event: Event) -> None:
        if self.reader.at_eof():
            if self.on_close:
                self.on_close(self)
            raise DisconnectedError()
        write_chunk(self.writer, bytes(event))

    def disconnect(self) -> None:
        self.writer.close()


_filter_re = re.compile(r"^([a-z.-]+)(=|>=|<=)(.*)$")
_comparators = {
    "=": lambda v1, v2: v1 == v2,
    ">=": lambda v1, v2: v1 >= v2,
    "<=": lambda v1, v2: v1 <= v2,
}


def parse_filter(string: str) -> "Filter":
    def parse_value(v: str) -> Union[str, int, datetime.date]:
        if len(v) >= 2 and v.startswith("'") and v.endswith("'"):
            return v[1:-1]
        try:
            return parse_iso_date(v)
        except ValueError:
            pass
        return int(v)

    m = _filter_re.match(string)
    if not m:
        raise ValueError()
    field = m.group(1).replace(".", "/")
    comparator = _comparators[m.group(2)]
    value = parse_value(m.group(3))
    if type(value) == datetime.date:
        cls: Type[Filter] = DateFilter
    else:
        cls = Filter
    filter_ = cls(field, comparator, value)
    filter_.string = string
    return filter_


class Filter:

    def __init__(self, field: str, comparator: _Comparator,
                 value: Any) -> None:
        self._field = field
        self._comparator = comparator
        self._value = value
        self.string = ""

    def __call__(self, message: JsonValue) -> bool:
        try:
            v = self._get_value(message)
        except ValueError:
            return False
        return self._comparator(v, self._value)

    def __str__(self) -> str:
        return self.string

    def _get_value(self, message: JsonValue) -> Any:
        try:
            v = json_get(message, self._field, self.field_type)
        except (ValueError, TypeError):
            raise ValueError()
        return self.parse_value(v)

    @property
    def field_type(self) -> JsonType:
        return type(self._value)

    def parse_value(self, v: str) -> Any:
        return v


class DateFilter(Filter):

    @property
    def field_type(self) -> type:
        return str

    def parse_value(self, v: str) -> datetime.date:
        return parse_iso_date(v)


class ServerStats:

    def __init__(self) -> None:
        self.start_time = datetime.datetime.now()
        self.total_connections = 0


def json_stats(stats: ServerStats, listeners: Sequence[Listener]) \
        -> Dict[str, Any]:
    def json_connection(listener: Listener) -> Dict[str, Any]:
        c = {
            "subsystem": listener.subsystem,
            "filters": [str(f) for f in listener.filters],
            "connection-time": listener.connection_time.isoformat(),
            "remote-host": listener.remote_host,
        }
        if listener.referer:
            c["referer"] = listener.referer
        return c

    return {
        "start-time": stats.start_time.isoformat(),
        "total-connections": stats.total_connections,
        "connections": [
            json_connection(l) for l in listeners
        ],
    }
