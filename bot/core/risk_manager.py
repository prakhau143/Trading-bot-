import logging
from typing import List

from bot.exceptions import RiskLimitExceeded
from bot.models.order_models import OrderRequest

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(
        self,
        max_order_notional: float = 1000.0,
        max_leverage: int = 10,
        allowed_leverage: List[int] = None,
    ):
        self.max_order_notional = max_order_notional
        self.max_leverage = max_leverage
        self.allowed_leverage = allowed_leverage or [1, 2, 3, 5, 10]

    def validate_order(self, request: OrderRequest, mark_price: float) -> None:
        notional = request.estimated_notional(mark_price)
        if notional > self.max_order_notional:
            raise RiskLimitExceeded(
                f"Order notional {notional:.2f} USDT exceeds maximum allowed "
                f"{self.max_order_notional:.2f} USDT"
            )
        logger.info(
            "RISK_CHECK_PASSED",
            extra={"notional": notional, "limit": self.max_order_notional},
        )

    def validate_leverage(self, leverage: int) -> None:
        if leverage > self.max_leverage:
            raise RiskLimitExceeded(
                f"Leverage {leverage}x exceeds maximum allowed {self.max_leverage}x"
            )
        if leverage not in self.allowed_leverage:
            raise RiskLimitExceeded(
                f"Leverage {leverage}x is not in allowed values: {self.allowed_leverage}"
            )

    def validate_quantity(self, quantity: float) -> None:
        if quantity <= 0:
            raise RiskLimitExceeded("Quantity must be greater than zero")
