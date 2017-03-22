SOCKET_NAME = "/var/run/eventstreamd.sock"
EVENTS_HTTP_PORT = 8888

PING_INTERVAL = 20

CERT_FILE = "/etc/eventstreamd/ssl.crt"
KEY_FILE = "/etc/eventstreamd/ssl.key"


class Config:

    def __init__(self):
        self.socket_file = SOCKET_NAME
        self.cert_file = CERT_FILE
        self.key_file = KEY_FILE
        self.http_port = EVENTS_HTTP_PORT
        self.ping_interval = PING_INTERVAL
