class DisconnectedError(Exception):

    def __init__(self):
        super().__init__("connection lost")
