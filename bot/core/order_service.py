import logging
import time
from typing import Any, Dict, Optional

from bot.clients.binance_client import TradingClient
from bot.core.retry_handler import retry_api_call
from bot.core.risk_manager import RiskManager
from bot.exceptions import TradingBotError
from bot.models.order_models import (
    BracketOrderRequest,
    OrderRequest,
    OrderSide,
    OrderType,
)
from bot.repository.order_repo import OrderRepository

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(
        self,
        client: TradingClient,
        risk_manager: RiskManager,
        order_repo: OrderRepository,
    ):
        self.client = client
        self.risk_manager = risk_manager
        self.repo = order_repo

    def place_order(
        self,
        request: OrderRequest,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        logger.info(
            "ORDER_REQUESTED",
            extra={
                "symbol": request.symbol,
                "side": request.side.value,
                "type": request.order_type.value,
                "quantity": request.quantity,
                "dry_run": dry_run,
            },
        )

        mark_price = self.client.get_mark_price(request.symbol)
        self.risk_manager.validate_order(request, mark_price)

        notional = request.estimated_notional(mark_price)
        fee = request.estimated_fee(mark_price)

        if dry_run:
            result = {
                "status": "DRY_RUN",
                "symbol": request.symbol,
                "side": request.side.value,
                "type": request.order_type.value,
                "quantity": request.quantity,
                "estimated_notional_usdt": round(notional, 4),
                "estimated_fee_usdt": round(fee, 6),
            }
            self.repo.save(request, result, is_dry_run=True)
            logger.info("DRY_RUN_COMPLETE", extra=result)
            return result

        params = request.to_api_params()
        start = time.monotonic()
        response = retry_api_call(self.client.create_order, **params)
        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "ORDER_PLACED",
            extra={
                "order_id": response.get("orderId"),
                "status": response.get("status"),
                "latency_ms": f"{elapsed_ms:.0f}",
            },
        )
        response["_latency_ms"] = f"{elapsed_ms:.0f}ms"
        self.repo.save(request, response, is_dry_run=False)
        return response

    def place_bracket_order(
        self,
        req: BracketOrderRequest,
        dry_run: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        opposite = OrderSide.SELL if req.side == OrderSide.BUY else OrderSide.BUY

        entry = OrderRequest(
            symbol=req.symbol,
            side=req.side,
            order_type=OrderType.LIMIT,
            quantity=req.quantity,
            price=req.entry_price,
        )
        tp = OrderRequest(
            symbol=req.symbol,
            side=opposite,
            order_type=OrderType.TAKE_PROFIT_MARKET,
            quantity=req.quantity,
            stop_price=req.take_profit,
            reduce_only=True,
        )
        sl = OrderRequest(
            symbol=req.symbol,
            side=opposite,
            order_type=OrderType.STOP_MARKET,
            quantity=req.quantity,
            stop_price=req.stop_loss,
            reduce_only=True,
        )

        logger.info(
            "BRACKET_ORDER_REQUESTED",
            extra={
                "symbol": req.symbol,
                "side": req.side.value,
                "entry": req.entry_price,
                "tp": req.take_profit,
                "sl": req.stop_loss,
            },
        )

        results = {
            "entry": self.place_order(entry, dry_run=dry_run),
            "take_profit": self.place_order(tp, dry_run=dry_run),
            "stop_loss": self.place_order(sl, dry_run=dry_run),
        }
        return results

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        logger.info("CANCEL_ORDER_REQUESTED", extra={"symbol": symbol, "order_id": order_id})
        response = self.client.cancel_order(symbol=symbol, order_id=order_id)
        logger.info("ORDER_CANCELLED", extra={"order_id": order_id, "status": response.get("status")})
        return response
