import pytest
from pydantic import ValidationError

from bot.models.order_models import (
    BracketOrderRequest,
    OrderRequest,
    OrderSide,
    OrderType,
)


class TestOrderRequestValidation:
    def test_valid_market_buy(self):
        req = OrderRequest(
            symbol="btcusdt",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        assert req.symbol == "BTCUSDT"
        assert req.side == OrderSide.BUY

    def test_symbol_uppercased(self):
        req = OrderRequest(
            symbol="ethusdt",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.01,
        )
        assert req.symbol == "ETHUSDT"

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=-0.001,
            )

    def test_quantity_zero_rejected(self):
        with pytest.raises(ValidationError):
            OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0,
            )

    def test_limit_order_requires_price(self):
        with pytest.raises(ValidationError, match="price"):
            OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0.001,
            )

    def test_limit_order_with_price_valid(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=60000.0,
        )
        assert req.price == 60000.0

    def test_stop_market_requires_stop_price(self):
        with pytest.raises(ValidationError, match="stop_price"):
            OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.STOP_MARKET,
                quantity=0.001,
            )

    def test_stop_market_with_stop_price_valid(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_MARKET,
            quantity=0.001,
            stop_price=58000.0,
        )
        assert req.stop_price == 58000.0

    def test_to_api_params_market(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        params = req.to_api_params()
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["type"] == "MARKET"
        assert "timeInForce" not in params

    def test_to_api_params_limit_has_time_in_force(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=60000.0,
        )
        params = req.to_api_params()
        assert params["timeInForce"] == "GTC"
        assert params["price"] == 60000.0

    def test_estimated_notional(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        assert req.estimated_notional(mark_price=60000.0) == pytest.approx(60.0)

    def test_estimated_fee(self):
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        fee = req.estimated_fee(mark_price=60000.0, taker_rate=0.0004)
        assert fee == pytest.approx(0.024)


class TestBracketOrderValidation:
    def test_valid_buy_bracket(self):
        req = BracketOrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            entry_price=60000,
            take_profit=62000,
            stop_loss=59000,
        )
        assert req.symbol == "BTCUSDT"

    def test_buy_bracket_tp_below_entry_rejected(self):
        with pytest.raises(ValidationError, match="take_profit must be above"):
            BracketOrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=0.001,
                entry_price=60000,
                take_profit=59000,  # wrong: below entry for BUY
                stop_loss=58000,
            )

    def test_buy_bracket_sl_above_entry_rejected(self):
        with pytest.raises(ValidationError, match="stop_loss must be below"):
            BracketOrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=0.001,
                entry_price=60000,
                take_profit=62000,
                stop_loss=61000,  # wrong: above entry for BUY
            )

    def test_sell_bracket_valid(self):
        req = BracketOrderRequest(
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            quantity=0.01,
            entry_price=3000,
            take_profit=2900,  # below entry for SELL
            stop_loss=3100,    # above entry for SELL
        )
        assert req.side == OrderSide.SELL
