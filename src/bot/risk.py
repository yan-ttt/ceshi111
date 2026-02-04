from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskSettings:
    stop_loss_pct: float
    take_profit_pct: float
    max_drawdown_pct: float
    dynamic_position: bool


@dataclass
class RiskPlan:
    stop_loss: float
    take_profit: float
    position_size: float


class RiskManager:
    def __init__(self, settings: RiskSettings) -> None:
        self.settings = settings

    def compute_plan(
        self,
        entry_price: float,
        base_size: float,
        volatility: Optional[float] = None,
    ) -> RiskPlan:
        position_size = base_size
        if self.settings.dynamic_position and volatility is not None:
            # Lower position size when volatility increases
            position_size = max(base_size * (1.0 / max(volatility, 1e-6)), base_size * 0.2)
        stop_loss = entry_price * (1 - self.settings.stop_loss_pct)
        take_profit = entry_price * (1 + self.settings.take_profit_pct)
        return RiskPlan(
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
        )
