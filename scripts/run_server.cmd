@echo off
if not exist .\.venv\Scripts\activate.bat (
  echo Virtualenv not found. Run .\scripts\windows_setup.cmd first.
  exit /b 1
)
call .\.venv\Scripts\activate.bat
set PYTHONPATH=src
python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
