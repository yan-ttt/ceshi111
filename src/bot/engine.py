from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from bot.ai_models import ModelRegistry, OnlineLinearModel, Signal, WeightedEnsembleModel
from bot.config import Settings
from bot.gate_api import GateAPI, GateCredentials
from bot.risk import RiskManager, RiskPlan, RiskSettings
from bot.storage import ModelState, StateStore
from bot.logging_utils import TradeLogger
from bot.training import HybridTrainer, TrainingReport


@dataclass
class TradeDecision:
    symbol: str
    action: str
    confidence: float
    rationale: str
    target_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Position:
    symbol: str
    entry_price: float
    size: float


class TradingEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = ModelRegistry()
        self.model_weights: Dict[str, float] = {name: 1.0 for name in self.registry.list_models()}
        self.model_scores: Dict[str, float] = {name: 0.0 for name in self.registry.list_models()}
        self.ensemble: WeightedEnsembleModel = self.registry.get_weighted_ensemble(self.model_weights)
        self._last_signals: Dict[str, Signal] = {}
        self.positions: Dict[str, Position] = {}
        self.risk_manager = RiskManager(
            RiskSettings(
                stop_loss_pct=settings.stop_loss_pct,
                take_profit_pct=settings.take_profit_pct,
                max_drawdown_pct=settings.max_drawdown_pct,
                dynamic_position=settings.dynamic_position,
            )
        )
        self.gate_api = GateAPI(
            GateCredentials(
                api_key=settings.gate_api_key,
                api_secret=settings.gate_api_secret,
                api_host=settings.gate_api_host,
            ),
            max_retries=settings.max_retries,
            retry_backoff_s=settings.retry_backoff_s,
        )
        self.paper_api = GateAPI(
            GateCredentials(
                api_key=settings.paper_api_key,
                api_secret=settings.paper_api_secret,
                api_host=settings.paper_api_host,
            ),
            max_retries=settings.max_retries,
            retry_backoff_s=settings.retry_backoff_s,
        )
        self.state_store = StateStore(settings.state_dir)
        self.trade_logger = TradeLogger(settings.log_dir)
        self._cycle_count = 0
        self._balances: Dict[str, float] = {}
        self._positions: Dict[str, Dict[str, float]] = {}
        self._last_cycle_ms: float = 0.0
        self._last_training: TrainingReport | None = None
        # 混合训练器（可用 GPU/CPU）
        self.trainer = HybridTrainer(settings.training_device)
        self._load_state()

    @property
    def last_signals(self) -> Dict[str, Signal]:
        return self._last_signals

    def fetch_candles(self, symbol: str) -> pd.DataFrame:
        api = self.paper_api if self.settings.enable_paper_trade else self.gate_api
        data = api.fetch_spot_candles(
            symbol,
            self.settings.candle_interval,
            self.settings.candle_limit,
        )
        if not data:
            raise ValueError("empty candle data")
        columns = ["timestamp", "volume", "close", "high", "low", "open"]
        candles = pd.DataFrame(data, columns=columns)
        for col in ["open", "high", "low", "close", "volume"]:
            candles[col] = pd.to_numeric(candles[col], errors="coerce")
        return candles.dropna()

    def analyze(self, symbol: str) -> Signal:
        candles = self.fetch_candles(symbol)
        signal = self.ensemble.predict(candles, symbol)
        self._last_signals[symbol] = signal
        self._update_learning(candles)
        self._update_model_weights(candles)
        return signal

    def build_decision(self, signal: Signal) -> TradeDecision:
        candles = self.fetch_candles(signal.symbol)
        volatility = float(candles["close"].pct_change().tail(20).std())
        price = float(candles["close"].iloc[-1])
        base_size = self.settings.max_position_usdt
        risk_multiplier = 1.5 if self.settings.risk_level == "high" else 1.0
        target_size = base_size * signal.confidence * risk_multiplier
        plan: RiskPlan = self.risk_manager.compute_plan(price, target_size, volatility)
        return TradeDecision(
            symbol=signal.symbol,
            action=signal.direction,
            confidence=signal.confidence,
            rationale=signal.rationale,
            target_size=plan.position_size,
            stop_loss=plan.stop_loss,
            take_profit=plan.take_profit,
        )

    def execute(self, decision: TradeDecision) -> Dict[str, object]:
        if not self.settings.enable_auto_trade:
            return {"status": "skipped", "reason": "auto trade disabled"}
        response: Dict[str, object] = {"status": "queued", "action": decision.action}
        if self.settings.enable_paper_trade:
            response["paper"] = self._submit_orders(self.paper_api, decision, mode="paper")
        if self.settings.trading_mode != "paper":
            response["live"] = self._submit_orders(self.gate_api, decision, mode="live")
        return response

    def _submit_orders(self, api: GateAPI, decision: TradeDecision, mode: str) -> Dict[str, object]:
        receipts = []
        try:
            if self.settings.enable_spot:
                order = api.place_spot_order(
                    symbol=decision.symbol,
                    side="buy" if decision.action == "buy" else "sell",
                    amount=decision.target_size,
                )
                receipts.append(self._normalize_order(order, "spot"))
            if self.settings.enable_futures:
                order = api.place_futures_order(
                    contract=decision.symbol,
                    side="long" if decision.action == "buy" else "short",
                    size=decision.target_size,
                )
                receipts.append(self._normalize_order(order, "futures"))
        except Exception as exc:  # noqa: BLE001
            self.trade_logger.log_error(
                {
                    "mode": mode,
                    "decision": decision.__dict__,
                    "error": str(exc),
                    "context": "submit_orders",
                }
            )
            raise
        self.trade_logger.log_trade(
            {
                "mode": mode,
                "decision": decision.__dict__,
                "receipts": receipts,
            }
        )
        return {"status": "submitted", "receipts": receipts}

    def _normalize_order(self, payload: Dict[str, str], market: str) -> Dict[str, str]:
        return {
            "market": market,
            "id": str(payload.get("id", "")),
            "status": str(payload.get("status", "")),
            "raw": payload,
        }

    def _update_learning(self, candles: pd.DataFrame) -> None:
        # Target: next candle return as a simple supervised signal
        if len(candles) < 2:
            return
        target = float(candles["close"].pct_change().iloc[-1])
        for model in self.registry._models.values():
            model.update(candles, target)

    def _update_model_weights(self, candles: pd.DataFrame) -> None:
        if len(candles) < 2:
            return
        target = float(candles["close"].pct_change().iloc[-1])
        actual_direction = "buy" if target >= 0 else "sell"
        for name, model in self.registry._models.items():
            signal = model.predict(candles, "eval")
            score = 1.0 if signal.direction == actual_direction else -1.0
            prev = self.model_scores.get(name, 0.0)
            updated = self.settings.weight_ema_alpha * score + (1 - self.settings.weight_ema_alpha) * prev
            self.model_scores[name] = updated
            self.model_weights[name] = max(self.settings.min_model_weight, 1.0 + updated)

    def cycle_once(self) -> List[TradeDecision]:
        start = time.perf_counter()
        self._cycle_count += 1
        decisions = []
        for symbol in self.settings.symbols:
            signal = self.analyze(symbol)
            decisions.append(self.build_decision(signal))
        self._sync_state()
        self._last_cycle_ms = (time.perf_counter() - start) * 1000
        return decisions

    def run_forever(self, min_interval: float | None = None) -> None:
        interval_ms = self.settings.min_interval_ms if min_interval is None else min_interval * 1000
        while True:
            start = time.perf_counter()
            decisions = self.cycle_once()
            for decision in decisions:
                self.execute(decision)
            elapsed_ms = (time.perf_counter() - start) * 1000
            remaining = max(0.0, (interval_ms - elapsed_ms) / 1000)
            time.sleep(remaining)

    def stats(self) -> Dict[str, float]:
        return {
            "last_cycle_ms": self._last_cycle_ms,
        }

    # 混合训练入口：训练后写回在线线性模型参数
    def train_hybrid(self, symbol: str, epochs: int | None = None, device: str | None = None) -> TrainingReport:
        candles = self.fetch_candles(symbol)
        report = self.trainer.train(
            candles,
            epochs=epochs or self.settings.training_epochs,
            prefer_device=device or self.settings.training_device,
        )
        model = self.registry._models.get("online_linear")
        if isinstance(model, OnlineLinearModel):
            model.set_parameters(
                [report.weights["w1"], report.weights["w2"], report.weights["w3"], report.weights["w4"]],
                report.weights["bias"],
            )
        self._last_training = report
        return report

    def last_training(self) -> Dict[str, object]:
        if self._last_training is None:
            return {}
        return self._last_training.__dict__.copy()

    def _sync_state(self) -> None:
        if self._cycle_count % self.settings.save_interval != 0:
            return
        try:
            self._balances = self._fetch_balances()
            self._positions = self._fetch_positions()
        except Exception as exc:  # noqa: BLE001
            self.trade_logger.log_error({"error": str(exc), "context": "sync_state"})
        self._save_state()

    def _fetch_balances(self) -> Dict[str, float]:
        if self.settings.trading_mode == "paper":
            return {}
        balances = self.gate_api.list_spot_balances()
        result: Dict[str, float] = {}
        for item in balances:
            currency = item.get("currency")
            available = float(item.get("available", 0))
            result[currency] = available
        return result

    def _fetch_positions(self) -> Dict[str, Dict[str, float]]:
        if self.settings.trading_mode == "paper":
            return {}
        positions = self.gate_api.list_futures_positions()
        result: Dict[str, Dict[str, float]] = {}
        for item in positions:
            contract = item.get("contract")
            size = float(item.get("size", 0))
            entry_price = float(item.get("entry_price", 0))
            result[contract] = {"size": size, "entry_price": entry_price}
        return result

    def balances(self) -> Dict[str, float]:
        return self._balances

    def positions(self) -> Dict[str, Dict[str, float]]:
        return self._positions

    def get_spot_order_status(self, order_id: str, symbol: str) -> Dict[str, object]:
        return self.gate_api.get_spot_order(order_id, symbol)

    def get_futures_order_status(self, order_id: str) -> Dict[str, object]:
        return self.gate_api.get_futures_order(order_id)

    def _load_state(self) -> None:
        state = self.state_store.load()
        if state is None:
            return
        self.model_weights.update(state.weights)
        self.model_scores.update(state.scores)
        self.registry.load_online_state(state.online_linear)

    def _save_state(self) -> None:
        state = ModelState(
            weights=self.model_weights,
            scores=self.model_scores,
            online_linear=self.registry.online_state(),
        )
        self.state_store.save(state)
