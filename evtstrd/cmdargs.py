import argparse

from evtstrd.config import *


def parse_command_line():
    parser = argparse.ArgumentParser(
        description="A simple event stream server.")
    parser.add_argument(
        "-s", "--socket", default=SOCKET_NAME, help="socket file")
    parser.add_argument("--ssl-key", default=KEY_FILE, help="SSL key file")
    parser.add_argument(
        "--ssl-cert", default=CERT_FILE, help="SSL certificate file")
    parser.add_argument(
        "-p", "--port", default=HTTP_PORT, help="HTTP port", type=int)
    args = parser.parse_args()
    config = Config()
    config.socket_file = args.socket
    config.key_file = args.ssl_key
    config.cert_file = args.ssl_cert
    config.http_port = args.port
    return config
