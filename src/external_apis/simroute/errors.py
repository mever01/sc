class SimrouteError(Exception):
    """Base exception for Simroute API errors."""


class SimrouteAuthError(SimrouteError):
    """Raised when the API key is missing or invalid."""


class SimrouteNoNumbersError(SimrouteError):
    """Raised when no phone numbers are available for the requested country/service."""


class SimrouteBalanceError(SimrouteError):
    """Raised when the account balance is insufficient."""


class SimrouteTimeoutError(SimrouteError):
    """Raised when the SMS code does not arrive within the allowed time."""