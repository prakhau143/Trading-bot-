from functools import lru_cache

from bot.clients.binance_client import TradingClient
from bot.core.order_service import OrderService
from bot.core.risk_manager import RiskManager
from bot.repository.order_repo import OrderRepository
from bot.utils.config_loader import get_settings, load_yaml_config


@lru_cache(maxsize=1)
def get_trading_client() -> TradingClient:
    settings = get_settings()
    return TradingClient(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_secret_key,
        testnet=(settings.environment in ("testnet", "development")),
    )


@lru_cache(maxsize=1)
def get_risk_manager() -> RiskManager:
    settings = get_settings()
    yaml_cfg = load_yaml_config()
    risk_cfg = yaml_cfg.get("risk", {})
    return RiskManager(
        max_order_notional=risk_cfg.get(
            "max_order_notional_usdt", settings.max_order_size
        ),
        max_leverage=risk_cfg.get("max_leverage", settings.max_leverage),
        allowed_leverage=risk_cfg.get("allowed_leverage"),
    )


@lru_cache(maxsize=1)
def get_order_repository() -> OrderRepository:
    return OrderRepository()


@lru_cache(maxsize=1)
def get_order_service() -> OrderService:
    return OrderService(
        client=get_trading_client(),
        risk_manager=get_risk_manager(),
        order_repo=get_order_repository(),
    )
