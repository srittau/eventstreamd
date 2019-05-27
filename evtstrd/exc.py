class DisconnectedError(Exception):
    def __init__(self) -> None:
        super().__init__("connection lost")
