from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


PRICE_REQUIRED_TYPES = {OrderType.LIMIT, OrderType.STOP, OrderType.TAKE_PROFIT}
STOP_PRICE_REQUIRED_TYPES = {
    OrderType.STOP_MARKET,
    OrderType.TAKE_PROFIT_MARKET,
    OrderType.TRAILING_STOP_MARKET,
}


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Annotated[float, Field(gt=0, description="Order quantity (must be > 0)")]
    price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    reduce_only: bool = False

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_price_requirements(self) -> "OrderRequest":
        if self.order_type in PRICE_REQUIRED_TYPES and self.price is None:
            raise ValueError(
                f"'price' is required for {self.order_type.value} orders"
            )
        if self.order_type in STOP_PRICE_REQUIRED_TYPES and self.stop_price is None:
            raise ValueError(
                f"'stop_price' is required for {self.order_type.value} orders"
            )
        return self

    def to_api_params(self) -> dict:
        params: dict = {
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity,
        }
        if self.price is not None:
            params["price"] = self.price
        if self.stop_price is not None:
            params["stopPrice"] = self.stop_price
        if self.order_type == OrderType.LIMIT:
            params["timeInForce"] = "GTC"
        if self.reduce_only:
            params["reduceOnly"] = "true"
        return params

    def estimated_notional(self, mark_price: float) -> float:
        effective_price = self.price or mark_price
        return self.quantity * effective_price

    def estimated_fee(self, mark_price: float, taker_rate: float = 0.0004) -> float:
        return self.estimated_notional(mark_price) * taker_rate


class BracketOrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    quantity: Annotated[float, Field(gt=0)]
    entry_price: Annotated[float, Field(gt=0)]
    take_profit: Annotated[float, Field(gt=0)]
    stop_loss: Annotated[float, Field(gt=0)]

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_tp_sl_logic(self) -> "BracketOrderRequest":
        if self.side == OrderSide.BUY:
            if self.take_profit <= self.entry_price:
                raise ValueError("take_profit must be above entry_price for BUY orders")
            if self.stop_loss >= self.entry_price:
                raise ValueError("stop_loss must be below entry_price for BUY orders")
        else:
            if self.take_profit >= self.entry_price:
                raise ValueError("take_profit must be below entry_price for SELL orders")
            if self.stop_loss <= self.entry_price:
                raise ValueError("stop_loss must be above entry_price for SELL orders")
        return self
