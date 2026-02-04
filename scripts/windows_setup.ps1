Write-Host "[1/4] Create virtual environment..."
python -m venv .venv

Write-Host "[2/4] Activate virtual environment..."
$activate = ".\.venv\Scripts\Activate.ps1"
if (-Not (Test-Path $activate)) {
  Write-Host "Cannot find venv activation script. Please check that Python is installed."
  exit 1
}
& $activate

Write-Host "[3/4] Install dependencies..."
python -m pip install -r requirements.txt

Write-Host "[4/4] Initialize .env file..."
if (-Not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host ".env created. Please edit and fill in API keys."
} else {
  Write-Host "Existing .env detected. Skipping."
}

Write-Host "Done. Run: python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080"
