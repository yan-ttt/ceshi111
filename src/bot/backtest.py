from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from bot.ai_models import EnsembleModel
from bot.risk import RiskManager, RiskPlan, RiskSettings


@dataclass
class BacktestResult:
    symbol: str
    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    avg_trade_return: float


class Backtester:
    def __init__(self, model: EnsembleModel, risk_settings: RiskSettings) -> None:
        self.model = model
        self.risk_manager = RiskManager(risk_settings)

    def run(self, candles: pd.DataFrame, symbol: str) -> BacktestResult:
        capital = 1_000.0
        peak = capital
        position = 0.0
        entry_price = 0.0
        trades = 0
        wins = 0
        trade_returns: List[float] = []

        for idx in range(30, len(candles)):
            window = candles.iloc[: idx + 1]
            signal = self.model.predict(window, symbol)
            price = float(window["close"].iloc[-1])
            volatility = float(window["close"].pct_change().tail(20).std())

            if position == 0 and signal.direction == "buy":
                base_size = capital * 0.1
                plan: RiskPlan = self.risk_manager.compute_plan(price, base_size, volatility)
                position = plan.position_size / price
                entry_price = price
                capital -= plan.position_size
                trades += 1
            elif position > 0:
                stop_loss = entry_price * (1 - self.risk_manager.settings.stop_loss_pct)
                take_profit = entry_price * (1 + self.risk_manager.settings.take_profit_pct)
                if price <= stop_loss or price >= take_profit or signal.direction == "sell":
                    trade_return = (price - entry_price) / entry_price if entry_price else 0
                    trade_returns.append(trade_return)
                    if trade_return > 0:
                        wins += 1
                    capital += position * price
                    position = 0.0

            peak = max(peak, capital)

        if position > 0:
            capital += position * float(candles["close"].iloc[-1])

        total_return = (capital - 1_000.0) / 1_000.0
        drawdown = (peak - capital) / peak if peak > 0 else 0.0
        win_rate = wins / trades if trades else 0.0
        avg_trade_return = float(sum(trade_returns) / len(trade_returns)) if trade_returns else 0.0

        return BacktestResult(
            symbol=symbol,
            total_return=total_return,
            max_drawdown=drawdown,
            trades=trades,
            win_rate=win_rate,
            avg_trade_return=avg_trade_return,
        )

    def run_multi(self, data: Dict[str, pd.DataFrame]) -> List[BacktestResult]:
        return [self.run(candles, symbol) for symbol, candles in data.items()]
