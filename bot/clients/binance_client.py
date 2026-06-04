import logging
from typing import Any, Dict, List, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from bot.exceptions import BinanceAPIError, NetworkError

logger = logging.getLogger(__name__)

TESTNET_FUTURES_URL = "https://testnet.binancefuture.com/fapi"
TESTNET_FUTURES_DATA_URL = "https://testnet.binancefuture.com/futures/data"


class TradingClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self._client = Client(api_key=api_key, api_secret=api_secret)
        if testnet:
            self._client.FUTURES_URL = TESTNET_FUTURES_URL
            self._client.FUTURES_DATA_URL = TESTNET_FUTURES_DATA_URL

    def _call(self, method_name: str, **kwargs) -> Any:
        try:
            method = getattr(self._client, method_name)
            return method(**kwargs)
        except BinanceAPIException as exc:
            # NOTE: "msg" is a reserved LogRecord field — use "error_msg" instead
            logger.error("BINANCE_API_ERROR", extra={"error_code": exc.code, "error_msg": exc.message})
            raise BinanceAPIError(f"[{exc.code}] {exc.message}", code=exc.code) from exc
        except BinanceRequestException as exc:
            logger.error("BINANCE_REQUEST_ERROR", extra={"error": str(exc)})
            raise NetworkError(str(exc)) from exc
        except Exception as exc:
            # Catches requests.ReadTimeout, ConnectionError, SSLError, etc.
            # that python-binance does not wrap internally.
            error_type = type(exc).__name__
            logger.error("NETWORK_ERROR", extra={"error_type": error_type, "error": str(exc)})
            raise NetworkError(f"{error_type}: {exc}") from exc

    # ── Connectivity ──────────────────────────────────────────────────────────

    def ping(self) -> bool:
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def get_server_time(self) -> int:
        result = self._call("get_server_time")
        return result.get("serverTime", 0)

    # ── Market Data ───────────────────────────────────────────────────────────

    def get_mark_price(self, symbol: str) -> float:
        data = self._call("futures_mark_price", symbol=symbol)
        return float(data["markPrice"])

    # ── Orders ────────────────────────────────────────────────────────────────

    def create_order(self, **kwargs) -> Dict[str, Any]:
        return self._call("futures_create_order", **kwargs)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return self._call("futures_cancel_order", symbol=symbol, orderId=order_id)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol
        return self._call("futures_get_open_orders", **kwargs)

    def get_all_orders(self, symbol: str, limit: int = 50) -> List[Dict]:
        return self._call("futures_get_all_orders", symbol=symbol, limit=limit)

    # ── Account ───────────────────────────────────────────────────────────────

    def get_account_balance(self) -> List[Dict]:
        return self._call("futures_account_balance")

    def get_account_info(self) -> Dict[str, Any]:
        return self._call("futures_account")

    def get_position_information(self, symbol: Optional[str] = None) -> List[Dict]:
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol
        return self._call("futures_position_information", **kwargs)

    def get_account_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        return self._call("futures_account_trades", symbol=symbol, limit=limit)

    # ── Risk Settings ─────────────────────────────────────────────────────────

    def change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        return self._call("futures_change_leverage", symbol=symbol, leverage=leverage)

    def change_margin_type(self, symbol: str, margin_type: str) -> Dict[str, Any]:
        return self._call(
            "futures_change_margin_type", symbol=symbol, marginType=margin_type
        )
