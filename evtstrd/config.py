import configparser


DEFAULT_CONFIG = "/etc/eventstreamd.conf"

SOCKET_NAME = "/var/run/eventstreamd.sock"
HTTP_PORT = 8888

PING_INTERVAL = 20

CERT_FILE = "/etc/eventstreamd/ssl.crt"
KEY_FILE = "/etc/eventstreamd/ssl.key"


class Config:

    def __init__(self):
        self.socket_file = SOCKET_NAME
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
