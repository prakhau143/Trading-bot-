import pytest

from bot.core.risk_manager import RiskManager
from bot.exceptions import RiskLimitExceeded
from bot.models.order_models import OrderRequest, OrderSide, OrderType


def make_market_order(quantity: float = 0.001) -> OrderRequest:
    return OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=quantity,
    )


class TestRiskManager:
    def setup_method(self):
        self.risk = RiskManager(
            max_order_notional=1000.0,
            max_leverage=10,
            allowed_leverage=[1, 2, 3, 5, 10],
        )

    def test_valid_order_passes(self):
        req = make_market_order(quantity=0.001)
        self.risk.validate_order(req, mark_price=60000.0)  # notional = 60 < 1000

    def test_order_exceeding_notional_rejected(self):
        req = make_market_order(quantity=0.02)  # 0.02 * 60000 = 1200 > 1000
        with pytest.raises(RiskLimitExceeded, match="exceeds maximum allowed"):
            self.risk.validate_order(req, mark_price=60000.0)

    def test_order_at_exact_limit_passes(self):
        req = make_market_order(quantity=1000 / 60000)
        self.risk.validate_order(req, mark_price=60000.0)

    def test_valid_leverage_passes(self):
        self.risk.validate_leverage(10)

    def test_leverage_exceeds_max_rejected(self):
        with pytest.raises(RiskLimitExceeded, match="exceeds maximum allowed"):
            self.risk.validate_leverage(20)

    def test_leverage_not_in_allowed_list_rejected(self):
        with pytest.raises(RiskLimitExceeded, match="not in allowed values"):
            self.risk.validate_leverage(7)  # 7 not in [1,2,3,5,10]

    def test_zero_quantity_rejected(self):
        with pytest.raises(RiskLimitExceeded):
            self.risk.validate_quantity(0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(RiskLimitExceeded):
            self.risk.validate_quantity(-1)

    def test_limit_order_uses_price_not_mark_price(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=60000.0,
        )
        # notional uses price (60000) not mark_price (80000)
        self.risk.validate_order(req, mark_price=80000.0)  # should pass (60 USDT)
