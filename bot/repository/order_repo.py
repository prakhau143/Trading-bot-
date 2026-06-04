import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from bot.core.correlation import get_correlation_id
from bot.models.db_models import Base, OrderRecord
from bot.models.order_models import OrderRequest

logger = logging.getLogger(__name__)

DB_PATH = "data/orders.db"


class OrderRepository:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)

    def save(
        self,
        request: OrderRequest,
        response: Dict[str, Any],
        is_dry_run: bool = False,
    ) -> None:
        order_id = str(response.get("orderId", f"DRY-{datetime.utcnow().timestamp()}"))
        record = OrderRecord(
            order_id=order_id,
            symbol=request.symbol,
            side=request.side.value,
            order_type=request.order_type.value,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            status=response.get("status", "DRY_RUN"),
            correlation_id=get_correlation_id(),
            is_dry_run=is_dry_run,
            created_at=datetime.utcnow(),
            response_raw=json.dumps(response),
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
        logger.info("ORDER_SAVED", extra={"order_id": order_id})

    def get_all(self) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            records = session.execute(select(OrderRecord)).scalars().all()
            return [r.to_dict() for r in records]

    def get_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            records = (
                session.execute(
                    select(OrderRecord).where(OrderRecord.symbol == symbol.upper())
                )
                .scalars()
                .all()
            )
            return [r.to_dict() for r in records]

    def get_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            record = session.execute(
                select(OrderRecord).where(OrderRecord.order_id == order_id)
            ).scalar_one_or_none()
            return record.to_dict() if record else None

    def count(self) -> int:
        with Session(self.engine) as session:
            return session.execute(select(OrderRecord)).scalars().all().__len__()
