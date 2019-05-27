import configparser
from configparser import NoOptionError
from typing import Optional

DEFAULT_CONFIG = "/etc/eventstreamd.conf"

SOCKET_NAME = "/var/run/eventstreamd.sock"
SOCKET_MODE = 0o0600

HTTP_PORT = 8888

PING_INTERVAL = 20


class Config:
    def __init__(self) -> None:
        self.socket_file = SOCKET_NAME
        self.socket_owner: Optional[str] = None
        self.socket_group: Optional[str] = None
        self.socket_mode = SOCKET_MODE
        self.cert_file: Optional[str] = None
        self.key_file: Optional[str] = None
        self.http_port = HTTP_PORT
        self.ping_interval = PING_INTERVAL
        self.debug = False

    @property
    def with_ssl(self) -> bool:
        return bool(self.cert_file) and bool(self.key_file)


def read_config(filename: str) -> Config:
    config = Config()
    parser = configparser.ConfigParser()
    with open(filename, "r") as f:
        parser.read_file(f)
        config.socket_file = parser.get(
            "General", "SocketFile", fallback=SOCKET_NAME
        )
        try:
            socket_mode = parser.get("General", "SocketMode")
        except NoOptionError:
            pass
        else:
            config.socket_mode = int(socket_mode, base=8)
        config.socket_owner = parser.get("General", "SocketOwner", fallback="")
        config.socket_group = parser.get("General", "SocketGroup", fallback="")
        config.cert_file = parser.get(
            "General", "SSLCertificateFile", fallback=""
        )
        config.key_file = parser.get("General", "SSLKeyFile", fallback="")
        config.http_port = parser.getint(
            "General", "HTTPPort", fallback=HTTP_PORT
        )
    return config


def read_default_config() -> Config:
    try:
        return read_config(DEFAULT_CONFIG)
    except FileNotFoundError:
        return Config()
