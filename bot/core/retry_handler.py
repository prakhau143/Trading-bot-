import logging
import time
from typing import Any, Callable, TypeVar

from bot.exceptions import BinanceAPIError, NetworkError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Network-level errors we always retry
_NETWORK_ERRORS = (ConnectionError, TimeoutError, OSError)

# Binance error codes that indicate a transient server-side problem (safe to retry)
_RETRYABLE_BINANCE_CODES = {
    0,      # Non-JSON response (502/503 HTML page from testnet)
    -1003,  # Too many requests
    -1021,  # Timestamp for request is outside the recvWindow
}


def retry_api_call(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Call *func* with *args*/**kwargs*, retrying up to 3 times on:
      - Network errors (ConnectionError, TimeoutError, OSError)
      - Binance server-side errors (502, rate-limit, timestamp drift)

    Uses exponential back-off: 1 s → 2 s → 4 s.
    All other BinanceAPIException codes are raised immediately.
    """
    from binance.exceptions import BinanceAPIException

    max_attempts = 3
    last_exc: Exception = Exception("Unknown error")

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)

        except BinanceAPIException as exc:
            if exc.code in _RETRYABLE_BINANCE_CODES:
                last_exc = exc
                wait = 2 ** (attempt - 1)   # 1 → 2 → 4
                logger.warning(
                    "API_RETRY",
                    extra={
                        "attempt": attempt,
                        "max": max_attempts,
                        "wait_sec": wait,
                        "error_code": exc.code,
                        "error": str(exc),
                    },
                )
                if attempt < max_attempts:
                    time.sleep(wait)
            else:
                # Non-retryable Binance error — surface immediately
                raise BinanceAPIError(f"[{exc.code}] {exc.message}", code=exc.code) from exc

        except _NETWORK_ERRORS as exc:
            last_exc = exc
            wait = 2 ** (attempt - 1)
            logger.warning(
                "NETWORK_RETRY",
                extra={"attempt": attempt, "max": max_attempts, "wait_sec": wait, "error": str(exc)},
            )
            if attempt < max_attempts:
                time.sleep(wait)

        except Exception as exc:
            # Unexpected error — do not retry
            raise BinanceAPIError(str(exc)) from exc

    raise NetworkError(
        f"API call failed after {max_attempts} attempts: {last_exc}"
    ) from last_exc
