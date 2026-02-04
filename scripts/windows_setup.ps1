Write-Host "[1/4] 创建虚拟环境..."
python -m venv .venv

Write-Host "[2/4] 激活虚拟环境..."
$activate = ".\\.venv\\Scripts\\Activate.ps1"
if (-Not (Test-Path $activate)) {
  Write-Host "找不到虚拟环境激活脚本，请确认 python 已正确安装。"
  exit 1
}
& $activate

Write-Host "[3/4] 安装依赖..."
python -m pip install -r requirements.txt

Write-Host "[4/4] 初始化 .env 文件..."
if (-Not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "已生成 .env，请编辑并填入 API Key。"
} else {
  Write-Host "检测到已存在 .env，跳过复制。"
}

Write-Host "完成。运行：python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080"
