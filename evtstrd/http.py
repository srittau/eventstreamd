import asyncio
from http import HTTPStatus
from typing import Tuple, Iterable, List

Header = Tuple[str, str]


class HTTPError(Exception):

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.headers: List[Header] = []


class BadRequestError(HTTPError):

    def __init__(self, message):
        super().__init__(HTTPStatus.BAD_REQUEST, message)


class CGIArgumentError(BadRequestError):

    def __init__(self, argument_name, message):
        full_message = f"{argument_name}: {message}"
        super().__init__(full_message)
        self.argument_name = argument_name


class NotFoundError(HTTPError):

    def __init__(self, path):
        message = f"'{path}' not found"
        super().__init__(HTTPStatus.NOT_FOUND, message)


class MethodNotAllowedError(HTTPError):

    def __init__(self, method):
        message = f"method {method} not allowed"
        super().__init__(HTTPStatus.METHOD_NOT_ALLOWED, message)
        self.method = method


@asyncio.coroutine
def read_http_head(reader):

    @asyncio.coroutine
    def read_line():
        l = yield from reader.readline()
        try:
            return l.decode("ascii").strip()
        except UnicodeDecodeError:
            raise BadRequestError("non-ASCII characters in header")

    @asyncio.coroutine
    def read_request_line():
        l = yield from read_line()
        try:
            m, p, http_tag = l.split(" ")
        except ValueError:
            raise BadRequestError("invalid request line")
        if http_tag != "HTTP/1.1":
            raise BadRequestError("unsupported HTTP version")
        if m not in ["HEAD", "GET", "POST", "PUT"]:
            raise NotImplementedError()
        return m, p

    def parse_header_line(l):
        try:
            return tuple(l.split(": ", maxsplit=1))
        except ValueError:
            raise BadRequestError("invalid header line")

    method, path = yield from read_request_line()
    headers = {}
    while True:
        line = yield from read_line()
        if not line:
            break
        he, va = parse_header_line(line)
        headers[he.lower()] = va

    return method, path, headers


def write_http_head(writer, code: HTTPStatus, headers: Iterable[Header]) \
        -> None:
    line = "HTTP/1.1 {} {}\r\n".format(code.value, code.phrase)
    writer.write(line.encode("ascii"))
    for h, v in headers:
        line = h.encode("ascii") + b": " + v.encode("ascii") + b"\r\n"
        writer.write(line)
    writer.write(b"\r\n")


def write_http_error(writer, exc: HTTPError) -> None:
    write_http_head(writer, exc.status, exc.headers)
    writer.write(bytes(str(exc), "utf-8"))
    writer.write(b"\r\n")


def write_chunk(writer, data) -> None:
    writer.write(bytes(hex(len(data))[2:], "ascii"))
    writer.write(b"\r\n")
    writer.write(data)
    writer.write(b"\r\n")
