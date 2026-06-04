import csv
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

REPORTS_DIR = "reports"


class ExportService:
    def __init__(self, export_dir: str = REPORTS_DIR):
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    def export_orders_csv(self, orders: List[Dict[str, Any]]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.export_dir, f"orders_{timestamp}.csv")

        if not orders:
            # NOTE: "filename" is a reserved LogRecord field — use "file_path" instead
            logger.warning("EXPORT_EMPTY", extra={"file_path": filename})
            open(filename, "w").close()
            return filename

        fieldnames = list(orders[0].keys())
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(orders)

        logger.info("EXPORT_COMPLETE", extra={"file_path": filename, "rows": len(orders)})
        return filename
