# Gate.io AI Trading Bot (Local)

> **免责声明 / Disclaimer**
> 该项目仅用于学习与研究。自动化交易存在巨大风险，可能导致资金损失。请在小额或模拟环境中充分验证后再决定是否真实交易。

## 目标与范围
- **本地程序**，单机单账户。
- **现货 + 合约** 支持（Gate.io API）。
- **高风险偏好 / 高频**：由 AI 模型和规则组合驱动，不基于固定时间间隔。
- **Web 控制台**：用于查看状态、信号、订单、手动开关等。
- **AI 分析**：多模型集成（规则模型 + 统计模型 + LLM 接口占位），输出统一信号。
- **交易对优先**：BTC/USDT、GT/USDT、SOL/USDT、ETH/USDT。

## 功能概览
- **AI 信号集成**：将多模型信号合并为一个决策，输出方向、置信度、理由。
- **交易引擎**：根据风险偏好、资金、仓位与信号生成下单指令。
- **回测模块**：基于历史 K 线验证策略表现与风控结果。
- **止损/止盈与动态仓位管理**：根据波动率动态调整仓位。
- **模型自学习权重**：根据近期判断准确度动态调整模型权重。
- **Gate.io API 客户端**：预留签名、请求与错误处理。
- **Web 控制台**：FastAPI，提供状态、信号、订单、风控开关。

## 快速开始
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pip install -e .
cp .env.example .env
python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
```

也可以直接运行 Linux/macOS 脚本：
```bash
./scripts/linux_setup.sh
```

安装完成后可用脚本快速启动：
```bash
./scripts/run_server.sh
```

## Windows PowerShell 快速开始
> 你遇到的 `source`/`pip` 报错属于 Windows 环境差异，请用以下命令：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
copy .env.example .env
python -m uvicorn bot.web:app --host 0.0.0.0 --port 8080
```

> 建议使用 Python 3.10 / 3.11 / 3.12（3.13+ 在 Windows 上安装 pandas/numpy 可能需要编译器）。 

### Windows 常见乱码/编码问题
- **推荐使用 CMD 脚本**（避免 PowerShell 编码问题）：  
  ```powershell
  .\scripts\windows_setup.cmd
  ```
- 如需使用 PowerShell，建议先执行：  
  ```powershell
  chcp 65001
  ```
  并确保 `windows_setup.ps1` 为 **UTF-8 with BOM**。

如果脚本执行被阻止，请先运行：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

也可以直接运行脚本（Windows 推荐 .cmd）：
```powershell
.\scripts\windows_setup.cmd
```

安装完成后可用脚本快速启动：
```powershell
.\scripts\run_server.cmd
```

如果要使用 PowerShell 脚本（.ps1），请确保脚本编码为 UTF-8 with BOM，或者直接使用上面的 .cmd：
```powershell
.\scripts\windows_setup.ps1
```

## 使用说明（本地）
1. 先配置 `.env`，填入 Gate.io API Key/Secret（仅本地保存，不要提交到仓库）。  
2. 默认是 `paper` 模式（不真实下单）。需要真实下单时，将 `TRADING_MODE=live` 并设置 `ENABLE_AUTO_TRADE=true`。  
3. 支持同时启用模拟交易与真实交易：`ENABLE_PAPER_TRADE=true` 且 `TRADING_MODE=live`，就会一边模拟一边真实下单。  
4. 用浏览器打开 `http://localhost:8080/` 进入可视化控制台。  
5. 需要查看接口文档时打开 `http://localhost:8080/docs`。  

### 行情与训练说明
- 行情数据通过 Gate 公共 K 线接口获取（`CANDLE_INTERVAL`/`CANDLE_LIMIT` 可配置）。  
- 模拟交易使用 `PAPER_API_*` 凭证，真实交易使用 `GATE_API_*`。  
- 模型权重与在线学习状态会保存到本地 `STATE_DIR`，下次启动自动加载。  
- 交易日志与错误日志写入 `LOG_DIR`（JSONL 格式）。  

### 常用接口
- `GET /status`：查看当前运行状态  
- `GET /signals`：获取最新 AI 交易信号  
- `GET /models`：查看模型权重、评分与可用模型  
- `GET /metrics`：查看运行延迟等指标  
- `GET /balances`：查看账户余额（仅真实交易模式有效）  
- `GET /positions`：查看合约持仓（仅真实交易模式有效）  
- `GET /orders/spot/{order_id}?symbol=BTC_USDT`：查询现货订单状态  
- `GET /orders/futures/{order_id}`：查询合约订单状态  
- `POST /cycle`：触发一次分析 + 执行  
- `POST /backtest`：对当前历史数据进行回测（包含收益率、胜率等统计）  

## 环境变量
见 `.env.example`。

### 可靠性/重试
- 下单与请求支持自动重试（`MAX_RETRIES`/`RETRY_BACKOFF_S`）。  
- 仍建议先用模拟交易验证策略，再开启真实交易。  

### 毫秒级执行说明
- 可通过 `MIN_INTERVAL_MS` 控制主循环最小间隔（默认 500ms）。  
- 受限于交易所速率限制与网络延迟，**真正毫秒级撮合/成交不可保证**，该参数主要用于高频信号刷新。  

### 深度模型说明
- 当前仅提供序列模型占位，若需 GPU/CPU 混合训练，可接入 PyTorch 等框架并加载训练权重。  

## 运行结构
- `bot.web`：Web 控制台
- `bot.engine`：交易引擎
- `bot.ai_models`：AI 信号模型
- `bot.backtest`：回测模块
- `bot.risk`：风控与仓位管理
- `bot.gate_api`：Gate.io API 客户端

## 风险说明
- 该示例默认**不会自动真实下单**，请在配置中显式开启。
- 高频和高风险偏好可能会在极端行情中造成严重亏损。
- 序列模型仅为占位（需要离线训练后接入权重）。在线学习模块为简化示例。

## 免责声明
使用本项目即表示您理解并接受相关风险。
