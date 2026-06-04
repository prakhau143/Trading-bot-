from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[str] = mapped_column(String(10))
    order_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    response_raw: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def to_dict(self) -> dict:
        import json as _json
        d = {
            "order_id":      self.order_id,
            "symbol":        self.symbol,
            "side":          self.side,
            "type":          self.order_type,
            "quantity":      self.quantity,
            "price":         self.price,
            "stop_price":    self.stop_price,
            "status":        self.status,
            "correlation_id": self.correlation_id,
            "is_dry_run":    self.is_dry_run,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "avg_price":     None,
        }
        # Recover avgPrice from the stored Binance response JSON
        if self.response_raw:
            try:
                raw = _json.loads(self.response_raw)
                avg = raw.get("avgPrice")
                if avg is not None:
                    fv = float(avg)
                    if fv > 0:
                        d["avg_price"] = round(fv, 6)
            except Exception:
                pass
        return d
