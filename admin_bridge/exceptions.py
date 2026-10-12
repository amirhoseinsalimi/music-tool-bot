"""Errors returned by the optional administrative bridge."""


class BridgeError(Exception):
    """Carries an HTTP status and a safe, public error message."""

    def __init__(self, status: int, message: str) -> None:
        """
        Creates an error that the bridge can return to its caller.

        :param status: int: The HTTP response status
        :param message: str: The public error message, without credentials or user data
        """
        super().__init__(message)

        self.status = status
