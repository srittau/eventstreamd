import logging
import sys

from evtstrd.cmdargs import parse_command_line
from evtstrd.exc import ServerAlreadyRunningError
from evtstrd.server import run_server


def main() -> None:
    config = parse_command_line()
    logging.getLogger("asyncio").disabled = not config.debug
    if config.debug:
        logging.root.setLevel(logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.DEBUG)
    try:
        run_server(config)
    except ServerAlreadyRunningError:
        print("server already running, exiting", file=sys.stderr)
        sys.exit(1)
