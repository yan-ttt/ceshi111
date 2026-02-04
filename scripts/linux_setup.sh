#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Check Python version..."
python - <<'PY'
import sys
v = sys.version_info
if not (v.major == 3 and v.minor in (10, 11, 12)):
    raise SystemExit("Please use Python 3.10, 3.11, or 3.12.")
PY

echo "[2/4] Create virtual environment..."
python -m venv .venv

if [ -f .venv/bin/activate ]; then
  echo "[3/4] Activate virtual environment..."
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "Cannot find .venv/bin/activate."
  exit 1
fi

echo "[4/4] Install dependencies..."
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env created. Please edit and fill in API keys."
else
  echo "Existing .env detected. Skipping."
fi

echo "Done. Run: python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080"
