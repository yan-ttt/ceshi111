from __future__ import annotations

from bot.config import load_settings
from bot.engine import TradingEngine


def main() -> None:
    settings = load_settings()
    engine = TradingEngine(settings)
    engine.run_forever()


if __name__ == "__main__":
    main()
