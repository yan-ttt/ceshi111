@echo off
echo [1/4] Create virtual environment...
python -m venv .venv

echo [2/4] Activate virtual environment...
call .\.venv\Scripts\activate.bat

echo [3/4] Install dependencies...
python -m pip install -r requirements.txt

echo [4/4] Initialize .env file...
if not exist .env (
  copy .env.example .env
  echo .env created. Please edit and fill in API keys.
) else (
  echo Existing .env detected. Skipping.
)

echo Done. Run: python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
