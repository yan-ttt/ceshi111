from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass
class TrainingReport:
    epochs: int
    samples: int
    loss: float
    device: str
    backend: str
    cpu_preprocess: bool
    weights: Dict[str, float]


class HybridTrainer:
    def __init__(self, prefer_device: str = "auto") -> None:
        self.prefer_device = prefer_device

    # 检查是否安装了 torch（用于 GPU/CPU 训练后端）
    def _torch_available(self) -> bool:
        return importlib.util.find_spec("torch") is not None

    # 根据偏好选择设备：优先 GPU，其次 CPU
    def _resolve_device(self, prefer: str) -> str:
        if not self._torch_available():
            return "cpu"
        import torch

        if prefer == "cpu":
            return "cpu"
        if prefer == "cuda" and torch.cuda.is_available():
            return "cuda"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    # 构建训练数据集（特征 + 下一根K线收益率作为目标）
    def _build_dataset(self, candles: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        close = candles["close"].astype(float)
        returns = close.pct_change().fillna(0.0)
        rolling_5 = returns.rolling(5).mean().fillna(0.0)
        rolling_10 = returns.rolling(10).mean().fillna(0.0)
        vol_10 = returns.rolling(10).std().fillna(0.0)
        momentum_5 = close.diff(5).fillna(0.0) / close.shift(5).replace(0, np.nan)
        momentum_5 = momentum_5.fillna(0.0)
        target = returns.shift(-1).fillna(0.0)
        features = np.column_stack(
            [
                rolling_5.values,
                rolling_10.values,
                vol_10.values,
                momentum_5.values,
            ]
        )
        valid = np.isfinite(features).all(axis=1)
        valid &= np.isfinite(target.values)
        features = features[valid]
        target_values = target.values[valid]
        if len(target_values) > 1:
            features = features[:-1]
            target_values = target_values[:-1]
        return features.astype(float), target_values.astype(float)

    # 执行混合训练：CPU 预处理 + torch 或 numpy 后端
    def train(
        self,
        candles: pd.DataFrame,
        epochs: int = 30,
        prefer_device: str | None = None,
        learning_rate: float = 0.05,
    ) -> TrainingReport:
        features, targets = self._build_dataset(candles)
        if len(targets) < 10:
            raise ValueError("not enough samples for training")
        device = self._resolve_device(prefer_device or self.prefer_device)
        backend = "numpy"
        cpu_preprocess = True
        mean = features.mean(axis=0)
        std = features.std(axis=0) + 1e-6
        features = (features - mean) / std
        if self._torch_available():
            import torch

            backend = "torch"
            x_tensor = torch.tensor(features, dtype=torch.float32)
            y_tensor = torch.tensor(targets, dtype=torch.float32).view(-1, 1)
            if device == "cuda":
                x_tensor = x_tensor.to(device)
                y_tensor = y_tensor.to(device)
            weights = torch.zeros((features.shape[1], 1), device=device, requires_grad=True)
            bias = torch.zeros((1,), device=device, requires_grad=True)
            optimizer = torch.optim.SGD([weights, bias], lr=learning_rate)
            for _ in range(max(1, epochs)):
                optimizer.zero_grad()
                pred = x_tensor @ weights + bias
                loss = torch.mean((pred - y_tensor) ** 2)
                loss.backward()
                optimizer.step()
            final_loss = float(loss.detach().cpu().item())
            learned_weights = weights.detach().cpu().view(-1).numpy()
            learned_bias = float(bias.detach().cpu().item())
        else:
            learned_weights = np.zeros(features.shape[1], dtype=float)
            learned_bias = 0.0
            final_loss = 0.0
            for _ in range(max(1, epochs)):
                preds = features @ learned_weights + learned_bias
                errors = preds - targets
                final_loss = float(np.mean(errors**2))
                grad_w = (2.0 / len(targets)) * (features.T @ errors)
                grad_b = float(2.0 * np.mean(errors))
                learned_weights -= learning_rate * grad_w
                learned_bias -= learning_rate * grad_b
        return TrainingReport(
            epochs=epochs,
            samples=int(len(targets)),
            loss=final_loss,
            device=device,
            backend=backend,
            cpu_preprocess=cpu_preprocess,
            weights={
                "w1": float(learned_weights[0]),
                "w2": float(learned_weights[1]),
                "w3": float(learned_weights[2]),
                "w4": float(learned_weights[3]),
                "bias": float(learned_bias),
            },
        )
