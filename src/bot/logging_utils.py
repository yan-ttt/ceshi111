from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class TradeLogger:
    def __init__(self, log_dir: str) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trade_log = self.log_dir / "trades.jsonl"
        self.error_log = self.log_dir / "errors.jsonl"

    def log_trade(self, payload: Dict[str, Any]) -> None:
        record = {"ts": datetime.utcnow().isoformat(), **payload}
        with self.trade_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_error(self, payload: Dict[str, Any]) -> None:
        record = {"ts": datetime.utcnow().isoformat(), **payload}
        with self.error_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
