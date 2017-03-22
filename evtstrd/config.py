import configparser
from configparser import NoOptionError

DEFAULT_CONFIG = "/etc/eventstreamd.conf"

SOCKET_NAME = "/var/run/eventstreamd.sock"
SOCKET_MODE = 0o0600

HTTP_PORT = 8888

PING_INTERVAL = 20


class Config:

    def __init__(self):
        self.socket_file = SOCKET_NAME
        self.socket_owner = None
        self.socket_group = None
        self.socket_mode = SOCKET_MODE
        self.cert_file = None
        self.key_file = None
        self.http_port = HTTP_PORT
        self.ping_interval = PING_INTERVAL

    @property
    def with_ssl(self):
        return self.cert_file is not None and self.key_file is not None


def read_config(filename):
    config = Config()
    parser = configparser.ConfigParser()
    with open(filename, "r") as f:
        parser.read_file(f)
        config.socket_file = parser.get(
            "General", "SocketFile", fallback=SOCKET_NAME)
        try:
            socket_mode = parser.get("General", "SocketMode")
        except NoOptionError:
            pass
        else:
            config.socket_mode = int(socket_mode, base=8)
        config.socket_owner = parser.get(
            "General", "SocketOwner", fallback=None)
        config.socket_group = parser.get(
            "General", "SocketGroup", fallback=None)
        config.cert_file = parser.get(
            "General", "SSLCertificateFile", fallback=None)
        config.key_file = parser.get(
            "General", "SSLKeyFile", fallback=None)
        config.http_port = parser.getint(
            "General", "HTTPPort", fallback=HTTP_PORT)
    return config


def read_default_config():
    try:
        return read_config(DEFAULT_CONFIG)
    except FileNotFoundError:
        return Config()
