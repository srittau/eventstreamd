import configparser
from configparser import NoOptionError

DEFAULT_CONFIG = "/etc/eventstreamd.conf"

SOCKET_NAME = "/var/run/eventstreamd.sock"
SOCKET_MODE = 0o0600

HTTP_PORT = 8888
CERT_FILE = "/etc/eventstreamd/ssl.crt"
KEY_FILE = "/etc/eventstreamd/ssl.key"

PING_INTERVAL = 20


class Config:

    def __init__(self):
        self.socket_file = SOCKET_NAME
        self.socket_owner = None
        self.socket_group = None
        self.socket_mode = SOCKET_MODE
        self.cert_file = CERT_FILE
        self.key_file = KEY_FILE
        self.http_port = HTTP_PORT
        self.ping_interval = PING_INTERVAL


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
            "General", "SSLCertificateFile", fallback=CERT_FILE)
        config.key_file = parser.get(
            "General", "SSLKeyFile", fallback=KEY_FILE)
        config.http_port = parser.getint(
            "General", "HTTPPort", fallback=HTTP_PORT)
    return config


def read_default_config():
    try:
        return read_config(DEFAULT_CONFIG)
    except FileNotFoundError:
        return Config()
