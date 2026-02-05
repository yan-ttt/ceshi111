from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    rationale: str
    model: str


class BaseModel:
    name = "base"

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        raise NotImplementedError

    def update(self, candles: pd.DataFrame, target: float) -> None:
        return None


class TrendModel(BaseModel):
    name = "trend"

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        closes = candles["close"].values
        short = pd.Series(closes).rolling(window=5).mean().iloc[-1]
        long = pd.Series(closes).rolling(window=20).mean().iloc[-1]
        direction = "buy" if short > long else "sell"
        confidence = min(0.9, abs(short - long) / (long + 1e-8))
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=float(confidence),
            rationale="短期均线与长期均线交叉判断趋势。",
            model=self.name,
        )


class MomentumModel(BaseModel):
    name = "momentum"

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        returns = candles["close"].pct_change().dropna()
        momentum = returns.tail(10).mean()
        direction = "buy" if momentum > 0 else "sell"
        confidence = min(0.8, abs(momentum) * 10)
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=float(confidence),
            rationale="短期收益率均值判断动量。",
            model=self.name,
        )


class VolatilityModel(BaseModel):
    name = "volatility"

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        returns = candles["close"].pct_change().dropna()
        volatility = returns.tail(20).std()
        direction = "buy" if volatility < returns.tail(5).std() else "sell"
        confidence = min(0.7, float(volatility) * 5)
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            rationale="波动率变化判断趋势延续或衰竭。",
            model=self.name,
        )


class TechnicalModel(BaseModel):
    name = "technical"

    def _rsi(self, series: pd.Series, period: int = 14) -> float:
        delta = series.diff().dropna()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        avg_gain = gains.rolling(window=period).mean().iloc[-1]
        avg_loss = losses.rolling(window=period).mean().iloc[-1]
        rs = avg_gain / max(avg_loss, 1e-8)
        return 100 - (100 / (1 + rs))

    def _macd(self, series: pd.Series) -> float:
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        return float((ema12 - ema26).iloc[-1])

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        closes = candles["close"]
        rsi = self._rsi(closes)
        macd = self._macd(closes)
        score = (0.5 if rsi < 30 else -0.5 if rsi > 70 else 0.0) + (0.5 if macd > 0 else -0.5)
        direction = "buy" if score >= 0 else "sell"
        confidence = min(0.75, abs(score))
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=float(confidence),
            rationale="RSI 与 MACD 组合判断超买/超卖和趋势。",
            model=self.name,
        )


class EnsembleModel:
    def __init__(self, models: List[BaseModel]) -> None:
        self.models = models

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        signals = [model.predict(candles, symbol) for model in self.models]
        votes = sum(1 if s.direction == "buy" else -1 for s in signals)
        direction = "buy" if votes >= 0 else "sell"
        confidence = float(np.mean([s.confidence for s in signals]))
        rationale = " | ".join(f"{s.model}:{s.rationale}" for s in signals)
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            rationale=rationale,
            model="ensemble",
        )


class WeightedEnsembleModel:
    def __init__(self, models: Dict[str, BaseModel], weights: Dict[str, float]) -> None:
        self.models = models
        self.weights = weights

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        signals = []
        weighted_score = 0.0
        total_weight = 0.0
        for name, model in self.models.items():
            signal = model.predict(candles, symbol)
            signals.append(signal)
            weight = self.weights.get(name, 1.0)
            total_weight += weight
            weighted_score += weight * (1.0 if signal.direction == "buy" else -1.0) * signal.confidence
        direction = "buy" if weighted_score >= 0 else "sell"
        confidence = float(min(0.95, abs(weighted_score) / max(total_weight, 1e-6)))
        rationale = " | ".join(f"{s.model}:{s.rationale}" for s in signals)
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            rationale=rationale,
            model="weighted_ensemble",
        )


class OnlineLinearModel(BaseModel):
    name = "online_linear"

    def __init__(self) -> None:
        self.weights = np.zeros(4)
        self.bias = 0.0
        self.learning_rate = 0.05

    def _features(self, candles: pd.DataFrame) -> np.ndarray:
        close = candles["close"].values
        returns = pd.Series(close).pct_change().fillna(0)
        return np.array(
            [
                returns.tail(5).mean(),
                returns.tail(10).mean(),
                returns.tail(20).std(),
                (close[-1] - close[-5]) / max(close[-5], 1e-8),
            ],
            dtype=float,
        )

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        features = self._features(candles)
        score = float(np.dot(self.weights, features) + self.bias)
        direction = "buy" if score >= 0 else "sell"
        confidence = min(0.85, abs(score))
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            rationale="在线线性模型基于收益与波动特征给出方向。",
            model=self.name,
        )

    def update(self, candles: pd.DataFrame, target: float) -> None:
        features = self._features(candles)
        pred = float(np.dot(self.weights, features) + self.bias)
        error = target - pred
        self.weights += self.learning_rate * error * features
        self.bias += self.learning_rate * error

    def state_dict(self) -> Dict[str, float]:
        return {
            "weights": self.weights.tolist(),
            "bias": float(self.bias),
            "learning_rate": float(self.learning_rate),
        }

    def load_state(self, payload: Dict[str, float]) -> None:
        weights = payload.get("weights")
        if isinstance(weights, list):
            self.weights = np.array(weights, dtype=float)
        if "bias" in payload:
            self.bias = float(payload["bias"])
        if "learning_rate" in payload:
            self.learning_rate = float(payload["learning_rate"])

    def set_parameters(self, weights: List[float], bias: float) -> None:
        # 允许外部训练器更新参数
        if len(weights) == len(self.weights):
            self.weights = np.array(weights, dtype=float)
        self.bias = float(bias)


class SequenceModel(BaseModel):
    name = "sequence"

    def predict(self, candles: pd.DataFrame, symbol: str) -> Signal:
        # Placeholder for LSTM/Transformer model weights (offline training expected)
        close = candles["close"].values
        trend = close[-1] - close[-10]
        direction = "buy" if trend >= 0 else "sell"
        confidence = min(0.6, abs(trend) / max(close[-10], 1e-8))
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=float(confidence),
            rationale="序列模型占位：应替换为训练好的 LSTM/Transformer。",
            model=self.name,
        )


class ModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, BaseModel] = {
            "trend": TrendModel(),
            "momentum": MomentumModel(),
            "volatility": VolatilityModel(),
            "online_linear": OnlineLinearModel(),
            "sequence": SequenceModel(),
            "technical": TechnicalModel(),
        }

    def get_ensemble(self) -> EnsembleModel:
        return EnsembleModel(list(self._models.values()))

    def get_weighted_ensemble(self, weights: Dict[str, float]) -> WeightedEnsembleModel:
        return WeightedEnsembleModel(self._models, weights)

    def list_models(self) -> List[str]:
        return list(self._models.keys())

    def load_online_state(self, payload: Dict[str, float]) -> None:
        model = self._models.get("online_linear")
        if isinstance(model, OnlineLinearModel):
            model.load_state(payload)

    def online_state(self) -> Dict[str, float]:
        model = self._models.get("online_linear")
        if isinstance(model, OnlineLinearModel):
            return model.state_dict()
        return {}
