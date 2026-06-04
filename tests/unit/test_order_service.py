from unittest.mock import MagicMock, patch

import pytest

from bot.core.order_service import OrderService
from bot.core.risk_manager import RiskManager
from bot.exceptions import BinanceAPIError, RiskLimitExceeded
from bot.models.order_models import (
    BracketOrderRequest,
    OrderRequest,
    OrderSide,
    OrderType,
)


def make_service(mock_response=None):
    client = MagicMock()
    client.get_mark_price.return_value = 60000.0
    if mock_response is not None:
        client.create_order.return_value = mock_response

    risk = RiskManager(max_order_notional=5000.0, max_leverage=10)
    repo = MagicMock()
    return OrderService(client=client, risk_manager=risk, order_repo=repo), client, repo


class TestOrderService:
    def test_market_order_placed_successfully(self):
        mock_resp = {"orderId": 123, "status": "FILLED", "symbol": "BTCUSDT"}
        service, client, repo = make_service(mock_resp)

        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        response = service.place_order(req, dry_run=False)

        assert response["orderId"] == 123
        assert response["status"] == "FILLED"
        client.create_order.assert_called_once()
        repo.save.assert_called_once()

    def test_dry_run_does_not_call_api(self):
        service, client, repo = make_service()

        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        response = service.place_order(req, dry_run=True)

        assert response["status"] == "DRY_RUN"
        client.create_order.assert_not_called()

    def test_dry_run_saved_to_repo(self):
        service, client, repo = make_service()

        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )
        service.place_order(req, dry_run=True)
        repo.save.assert_called_once()
        _, call_kwargs = repo.save.call_args
        assert call_kwargs.get("is_dry_run") is True

    def test_risk_limit_raises_before_api_call(self):
        service, client, _ = make_service()
        # 0.1 BTC * 60000 = 6000 > 5000 limit
        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        with pytest.raises(RiskLimitExceeded):
            service.place_order(req)
        client.create_order.assert_not_called()

    def test_limit_order_params_include_price_and_tif(self):
        mock_resp = {"orderId": 456, "status": "NEW", "symbol": "BTCUSDT"}
        service, client, _ = make_service(mock_resp)

        req = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=55000.0,
        )
        service.place_order(req)

        call_kwargs = client.create_order.call_args[1]
        assert call_kwargs["price"] == 55000.0
        assert call_kwargs["timeInForce"] == "GTC"

    def test_bracket_order_places_three_legs(self):
        service, client, repo = make_service(
            {"orderId": 1, "status": "NEW", "symbol": "BTCUSDT"}
        )

        br = BracketOrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            entry_price=60000,
            take_profit=62000,
            stop_loss=59000,
        )
        results = service.place_bracket_order(br, dry_run=False)

        assert "entry" in results
        assert "take_profit" in results
        assert "stop_loss" in results
        assert client.create_order.call_count == 3

    def test_cancel_order_calls_client(self):
        service, client, _ = make_service()
        client.cancel_order.return_value = {"orderId": 99, "status": "CANCELED"}

        response = service.cancel_order("BTCUSDT", 99)
        assert response["status"] == "CANCELED"
        client.cancel_order.assert_called_once_with(symbol="BTCUSDT", order_id=99)
