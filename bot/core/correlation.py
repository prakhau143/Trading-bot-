import uuid
from contextvars import ContextVar
from datetime import datetime

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    cid = f"REQ-{timestamp}-{uuid.uuid4().hex[:6].upper()}"
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    return _correlation_id.get()
