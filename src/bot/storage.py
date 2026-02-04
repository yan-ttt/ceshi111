from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class ModelState:
    weights: Dict[str, float]
    scores: Dict[str, float]
    online_linear: Dict[str, Any]


class StateStore:
    def __init__(self, state_dir: str) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "model_state.json"

    def load(self) -> ModelState | None:
        if not self.state_path.exists():
            return None
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        return ModelState(
            weights=data.get("weights", {}),
            scores=data.get("scores", {}),
            online_linear=data.get("online_linear", {}),
        )

    def save(self, state: ModelState) -> None:
        payload = asdict(state)
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
