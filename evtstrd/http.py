import logging
from asyncio.streams import StreamWriter, StreamReader
from http import HTTPStatus
from typing import Tuple, Iterable, List, Dict

Header = Tuple[str, str]


class HTTPError(Exception):
    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        *,
        headers: Iterable[Header] = [],
    ) -> None:
        super().__init__(message)
        self.status = status
        self.headers: List[Header] = list(headers)


class BadRequestError(HTTPError):
    def __init__(self, message: str) -> None:
        super().__init__(HTTPStatus.BAD_REQUEST, message)


class CGIArgumentError(BadRequestError):
    def __init__(self, argument_name: str, message: str) -> None:
        full_message = f"{argument_name}: {message}"
        super().__init__(full_message)
        self.argument_name = argument_name


class NotFoundError(HTTPError):
    def __init__(self, path: str) -> None:
        message = f"'{path}' not found"
        super().__init__(HTTPStatus.NOT_FOUND, message)


class MethodNotAllowedError(HTTPError):
    def __init__(self, method: str) -> None:
        message = f"method {method} not allowed"
        super().__init__(HTTPStatus.METHOD_NOT_ALLOWED, message)
        self.method = method


async def read_http_head(
    reader: StreamReader
) -> Tuple[str, str, Dict[str, str]]:
    async def read_line() -> str:
        line_ = await reader.readline()
        try:
            return line_.decode("ascii").strip()
        except UnicodeDecodeError:
            raise BadRequestError("non-ASCII characters in header")

    async def read_request_line() -> Tuple[str, str]:
        line_ = await read_line()
        try:
            m, p, http_tag = line_.split(" ")
        except ValueError:
            raise BadRequestError("invalid request line")
        if http_tag != "HTTP/1.1":
            raise BadRequestError("unsupported HTTP version")
        if m not in ["HEAD", "GET", "POST", "PUT"]:
            raise NotImplementedError()
        return m, p

    def parse_header_line(li: str) -> Tuple[str, ...]:
        try:
            return tuple(li.split(": ", maxsplit=1))
        except ValueError:
            raise BadRequestError("invalid header line")

    method, path = await read_request_line()
    headers = {}
    while True:
        line = await read_line()
        if not line:
            break
        he, va = parse_header_line(line)
        headers[he.lower()] = va

    return method, path, headers


def write_http_head(
    writer: StreamWriter, code: HTTPStatus, headers: Iterable[Header]
) -> None:
    status_line = "HTTP/1.1 {} {}\r\n".format(code.value, code.phrase)
    writer.write(status_line.encode("ascii"))
    for h, v in headers:
        line = h.encode("ascii") + b": " + v.encode("ascii") + b"\r\n"
        writer.write(line)
    writer.write(b"\r\n")


def write_response(
    writer: StreamWriter,
    status: HTTPStatus,
    headers: Iterable[Header],
    body: str,
) -> None:
    write_http_head(writer, status, headers)
    writer.write(body.encode("utf-8"))


def write_http_error(writer: StreamWriter, exc: HTTPError) -> None:
    body = str(exc) + "\r\n"
    write_response(writer, exc.status, exc.headers, body)


def write_chunk(writer: StreamWriter, data: bytes) -> None:
    writer.write(bytes(hex(len(data))[2:], "ascii"))
    writer.write(b"\r\n")
    writer.write(data)
    writer.write(b"\r\n")
    encoded = (
        data.decode("utf-8", errors="ignore")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    logging.debug(f"wrote chunk to listener: {encoded}")


def write_last_chunk(writer: StreamWriter) -> None:
    write_chunk(writer, b"")
