class ServerAlreadyRunningError(Exception):
    def __init__(self) -> None:
        super().__init__("server already running")


class DisconnectedError(Exception):
    def __init__(self) -> None:
        super().__init__("connection lost")


class PluginError(Exception):
    def __init__(self, plugin: str, message: str) -> None:
        super().__init__(f"error in '{plugin}' plugin: {message}")
        self.plugin = plugin
