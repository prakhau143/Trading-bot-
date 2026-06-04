class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class ValidationError(TradingBotError):
    """Raised when input validation fails."""


class RiskLimitExceeded(TradingBotError):
    """Raised when an order violates risk management rules."""


class BinanceAPIError(TradingBotError):
    """Raised when the Binance API returns an error."""

    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


class NetworkError(TradingBotError):
    """Raised when a network/connectivity issue occurs."""


class ConfigurationError(TradingBotError):
    """Raised when configuration is missing or invalid."""


class OrderNotFoundError(TradingBotError):
    """Raised when a requested order cannot be found."""


class InsufficientBalanceError(TradingBotError):
    """Raised when account balance is too low to place an order."""
