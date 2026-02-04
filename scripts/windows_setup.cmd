@echo off
echo [1/4] Create virtual environment...
python -c "import sys; v=sys.version_info; sys.exit(0 if (v.major==3 and v.minor in (10,11,12)) else 1)"
if errorlevel 1 (
  echo Please use Python 3.10, 3.11, or 3.12. Python 3.13+ may fail to install pandas/numpy on Windows.
  exit /b 1
)
python -m venv .venv

echo [2/4] Activate virtual environment...
call .\.venv\Scripts\activate.bat

echo [3/4] Install dependencies...
python -m pip install -r requirements.txt
python -m pip install -e .

echo [4/4] Initialize .env file...
if not exist .env (
  copy .env.example .env
  echo .env created. Please edit and fill in API keys.
) else (
  echo Existing .env detected. Skipping.
)

echo Done. Run: python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
