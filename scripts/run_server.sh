#!/usr/bin/env bash
set -euo pipefail

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "Virtualenv not found. Run ./scripts/linux_setup.sh first."
  exit 1
fi

PYTHONPATH="$(pwd)/src" python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
