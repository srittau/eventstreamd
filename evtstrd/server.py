import asyncio
import asyncio.log
import datetime
import json
import re
import ssl
from collections import defaultdict
from email.utils import formatdate
from grp import getgrnam
from http import HTTPStatus
import logging
import os
import sys
from pwd import getpwnam
from typing import List
from urllib.parse import urlparse, parse_qs

from jsonget import json_get

from evtstrd.cmdargs import parse_command_line
from evtstrd.config import Config
from evtstrd.date import parse_iso_date
from evtstrd.events import JSONEvent, PingEvent
from evtstrd.exc import DisconnectedError
from evtstrd.http import \
    HTTPError, CGIArgumentError, NotFoundError, MethodNotAllowedError, \
    read_http_head, write_http_error, write_http_head, write_chunk, Header
from evtstrd.util import read_json_line


def run_notification_server():
    config = parse_command_line()
    asyncio.log.logger.disabled = True
    NotificationServer(config).run()


class NotificationServer:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._loop = asyncio.get_event_loop()
        self._listeners = defaultdict(list)
        self._stats = ServerStats()
        self._socket_handler = SocketHandler(self._listeners, loop=self._loop)
        self._http_handler = HTTPHandler(
            config, self._listeners, self._stats, loop=self._loop)

    def run(self):
        self._remove_stale_socket()
        try:
            self._run_loop()
        finally:
            try:
                os.remove(self._config.socket_file)
            except FileNotFoundError:
                pass

    def _remove_stale_socket(self):
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

    def _run_loop(self):
        self._start_socket()
        self._start_http_server()
        self._change_socket_permissions()
        self._loop.run_forever()

    def _start_socket(self):
        f = asyncio.start_unix_server(
            self._socket_handler.handle, path=self._config.socket_file)
        self._loop.run_until_complete(f)

    def _start_http_server(self):
        if self._config.with_ssl:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                self._config.cert_file, self._config.key_file)
        else:
            ssl_context = None
        f = asyncio.start_server(
            self._http_handler.handle, port=self._config.http_port,
            ssl=ssl_context)
        self._loop.run_until_complete(f)

    def _change_socket_permissions(self):
        os.chmod(self._config.socket_file, self._config.socket_mode)
        if self._config.socket_owner is None:
            new_owner = -1
        else:
            new_owner = getpwnam(self._config.socket_owner).pw_uid
        if self._config.socket_group is None:
            new_group = -1
        else:
            new_group = getgrnam(self._config.socket_group).gr_gid
        if new_owner != -1 or new_group != -1:
            os.chown(self._config.socket_file, new_owner, new_group)


class SocketHandler:

    def __init__(self, listeners, *, loop=None):
        self._listeners = listeners
        self._loop = loop or asyncio.get_event_loop()

    @asyncio.coroutine
    def handle(self, reader, writer):
        while True:
            try:
                message = yield from read_json_line(reader)
            except DisconnectedError:
                break
            action = json_get(message, "action", str)
            logging.debug("received a '{}' message".format(action))
            if action == "notify":
                self._notify_listeners_about_message(message)
            else:
                logging.warning("received unknown action '{}'".format(action))

    def _notify_listeners_about_message(self, message):
        try:
            subsystem, event, data, id = self._get_event_data(message)
        except ValueError:
            pass
        else:
            self._notify_listeners(subsystem, event, data, id)

    def _notify_listeners(self, subsystem, event_type, data, id):
        listeners = self._listeners[subsystem]
        # Copy the list of listeners, because it can be modified during the
        # iteration.
        for listener in listeners[:]:
            listener.notify(event_type, data, id)
        logging.info(
            "notified {} listeners about {} event in subsystem '{}'".format(
                len(listeners), event_type, subsystem))

    @staticmethod
    def _get_event_data(message):
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

    def __init__(self, config: Config, listeners, stats, *, loop=None) -> None:
        self._config = config
        self._listeners = listeners
        self._stats = stats
        self._loop = loop or asyncio.get_event_loop()

    @asyncio.coroutine
    def handle(self, reader, writer):
        try:
            method, path, headers = yield from read_http_head(reader)
            yield from self._handle_request(
                reader, writer, method, path, headers)
        except HTTPError as exc:
            write_http_error(writer, exc)
        writer.close()

    @asyncio.coroutine
    def _handle_request(self, reader, writer, method, path, headers):
        url = urlparse(path)
        if url.path == "/events":
            if method != "GET":
                raise MethodNotAllowedError(method)
            yield from self._handle_get_events(reader, writer, url, headers)
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

    @asyncio.coroutine
    def _handle_get_events(self, reader, writer, url, headers):
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
        yield from self._setup_listener(
            reader, writer, headers, subsystem, filters)

    @asyncio.coroutine
    def _setup_listener(self, reader, writer, headers, subsystem, filters):
        listener = self._create_listener(
            reader, writer, headers, subsystem, filters)
        self._listeners[subsystem].append(listener)
        self._stats.total_connections += 1
        yield from listener.ping_loop()

    def _create_listener(self, reader, writer, headers, subsystem, filters):
        logging.info("client subscribed to subsystem '{}'".format(subsystem))
        listener = Listener(
            self._config, reader, writer, subsystem, filters, loop=self._loop)
        listener.on_close = self._remove_listener
        listener.remote_host = writer.get_extra_info("peername")[0]
        listener.referer = headers.get("referer")
        return listener

    def _remove_listener(self, listener):
        logging.info(
            "client disconnected from subsystem '{}'".format(
                listener.subsystem))
        self._listeners[listener.subsystem].remove(listener)

    def _parse_event_args(self, query):
        args = parse_qs(query)
        if "subsystem" not in args:
            raise CGIArgumentError("subsystem", "missing argument")
        try:
            filters = [parse_filter(f) for f in args.get("filter", [])]
        except ValueError:
            raise CGIArgumentError("filter", "could not parse filter")
        return args["subsystem"][0], filters

    def _handle_get_stats(self, writer):
        all_listeners = []
        for key in self._listeners:
            all_listeners.extend(self._listeners[key])
        j = json_stats(self._stats, all_listeners)
        response = json.dumps(j).encode("utf-8")
        response_headers = self._default_headers() + [
            ("Connection", "close"),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response)))
        ]
        write_http_head(writer, HTTPStatus.OK, response_headers)
        writer.write(response)
        writer.close()


class Listener:

    def __init__(
            self, config: Config, reader, writer, subsystem, filters,
            *, loop=None) -> None:
        self._config = config
        self.loop = loop or asyncio.get_event_loop()
        self.subsystem = subsystem
        self.filters = filters
        self.reader = reader
        self.writer = writer
        self.on_close = None
        self.connection_time = datetime.datetime.now()
        self.remote_host = None
        self.referer = None

    def __repr__(self):
        return "<Listener 0x{:x} for {}>".format(id(self), self.subsystem)

    def notify(self, event_type, data, id=None):
        if all(f(data) for f in self.filters):
            event = JSONEvent(event_type, data, id)
            try:
                self._write_event(event)
            except DisconnectedError:
                pass

    @asyncio.coroutine
    def ping_loop(self):
        while True:
            try:
                self._write_event(PingEvent())
            except DisconnectedError:
                break
            yield from asyncio.sleep(
                self._config.ping_interval, loop=self.loop)

    def _write_event(self, event):
        if self.reader.at_eof():
            if self.on_close:
                self.on_close(self)
            raise DisconnectedError()
        write_chunk(self.writer, bytes(event))


_filter_re = re.compile(r"^([a-z.-]+)(=|>=|<=)(.*)$")
_comparators = {
    "=": lambda v1, v2: v1 == v2,
    ">=": lambda v1, v2: v1 >= v2,
    "<=": lambda v1, v2: v1 <= v2,
}


def parse_filter(string):
    def parse_value(v):
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
        cls = DateFilter
    else:
        cls = Filter
    filter_ = cls(field, comparator, value)
    filter_.string = string
    return filter_


class Filter:

    def __init__(self, field, comparator, value):
        self._field = field
        self._comparator = comparator
        self._value = value
        self.string = ""

    def __call__(self, message):
        try:
            v = self._get_value(message)
        except ValueError:
            return False
        return self._comparator(v, self._value)

    def __str__(self):
        return self.string

    def _get_value(self, message):
        try:
            v = json_get(message, self._field, self.field_type)
        except (ValueError, TypeError):
            raise ValueError()
        return self.parse_value(v)

    @property
    def field_type(self):
        return type(self._value)

    def parse_value(self, v):
        return v


class DateFilter(Filter):

    @property
    def field_type(self):
        return str

    def parse_value(self, v):
        return parse_iso_date(v)


class ServerStats:

    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.total_connections = 0


def json_stats(stats, listeners):
    def json_connection(listener):
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
