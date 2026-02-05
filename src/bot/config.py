from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    gate_api_key: str
    gate_api_secret: str
    gate_api_host: str
    trading_mode: str
    symbols: List[str]
    max_position_usdt: float
    risk_level: str
    enable_auto_trade: bool
    enable_futures: bool
    enable_spot: bool
    stop_loss_pct: float
    take_profit_pct: float
    max_drawdown_pct: float
    dynamic_position: bool
    weight_ema_alpha: float
    min_model_weight: float
    paper_api_key: str
    paper_api_secret: str
    paper_api_host: str
    enable_paper_trade: bool
    candle_interval: str
    candle_limit: int
    state_dir: str
    log_dir: str
    max_retries: int
    retry_backoff_s: float
    save_interval: int
    min_interval_ms: int
    training_device: str
    training_epochs: int



def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def load_settings() -> Settings:
    symbols = [s.strip() for s in os.getenv("SYMBOLS", "").split(",") if s.strip()]
    return Settings(
        gate_api_key=os.getenv("GATE_API_KEY", ""),
        gate_api_secret=os.getenv("GATE_API_SECRET", ""),
        gate_api_host=os.getenv("GATE_API_HOST", "https://api.gateio.ws"),
        trading_mode=os.getenv("TRADING_MODE", "paper"),
        symbols=symbols or ["BTC_USDT", "GT_USDT", "SOL_USDT", "ETH_USDT"],
        max_position_usdt=float(os.getenv("MAX_POSITION_USDT", "200")),
        risk_level=os.getenv("RISK_LEVEL", "high"),
        enable_auto_trade=_get_bool("ENABLE_AUTO_TRADE", False),
        enable_futures=_get_bool("ENABLE_FUTURES", True),
        enable_spot=_get_bool("ENABLE_SPOT", True),
        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.02")),
        take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "0.05")),
        max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.15")),
        dynamic_position=_get_bool("DYNAMIC_POSITION", True),
        weight_ema_alpha=float(os.getenv("WEIGHT_EMA_ALPHA", "0.2")),
        min_model_weight=float(os.getenv("MIN_MODEL_WEIGHT", "0.2")),
        paper_api_key=os.getenv("PAPER_API_KEY", ""),
        paper_api_secret=os.getenv("PAPER_API_SECRET", ""),
        paper_api_host=os.getenv("PAPER_API_HOST", "https://fx-api-testnet.gateio.ws"),
        enable_paper_trade=_get_bool("ENABLE_PAPER_TRADE", True),
        candle_interval=os.getenv("CANDLE_INTERVAL", "1m"),
        candle_limit=int(os.getenv("CANDLE_LIMIT", "200")),
        state_dir=os.getenv("STATE_DIR", "src/bot/state"),
        log_dir=os.getenv("LOG_DIR", "src/bot/logs"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        retry_backoff_s=float(os.getenv("RETRY_BACKOFF_S", "0.5")),
        save_interval=int(os.getenv("SAVE_INTERVAL", "5")),
        min_interval_ms=int(os.getenv("MIN_INTERVAL_MS", "500")),
        training_device=os.getenv("TRAINING_DEVICE", "auto"),
        training_epochs=int(os.getenv("TRAINING_EPOCHS", "30")),
    )
