# 使用文档 / Usage Guide

## 快速开始 / Quick Start
1. 复制 `.env.example` 为 `.env` 并填写你的 API。  
   Copy `.env.example` to `.env` and fill in your API credentials.
2. 安装依赖后启动服务：  
   Install dependencies and start the server:
   ```bash
   python -m uvicorn bot.web:app --host 0.0.0.0 --port 8000
   ```
3. 访问 `http://localhost:8000/` 查看控制台。  
   Visit `http://localhost:8000/` to open the dashboard.

## 关键配置 / Key Configuration
> 下面的字段中英文一一对应，修改 `.env` 后需要重启服务。  
> The fields below are bilingual. Restart the service after updating `.env`.

| 配置项 (中文) | Environment Key (English) | 说明 / Description |
| --- | --- | --- |
| 实盘/模拟模式 | `TRADING_MODE` | `paper`=模拟、`live`=实盘。`paper` 时会使用 `PAPER_API_*`。 |
| 启用自动交易 | `ENABLE_AUTO_TRADE` | `true` 才会执行下单，否则只分析不下单。 |
| 启用模拟下单 | `ENABLE_PAPER_TRADE` | `true` 时会走测试网交易。 |
| 交易对 | `SYMBOLS` | 逗号分隔，如 `BTC_USDT,ETH_USDT`。 |
| K线周期 | `CANDLE_INTERVAL` | 例如 `1m`、`15m`、`1h`。 |
| K线数量 | `CANDLE_LIMIT` | 拉取多少根K线。 |
| 最大仓位 | `MAX_POSITION_USDT` | 单笔最大 USDT 规模。 |
| 风险等级 | `RISK_LEVEL` | `high/medium/low`，影响仓位大小。 |
| 训练设备 | `TRAINING_DEVICE` | `auto/cpu/cuda`，混合训练设备选择。 |
| 训练轮数 | `TRAINING_EPOCHS` | 混合训练默认轮数。 |

## 常用接口 / Common Endpoints
| 接口 | 方法 | 说明 / Description |
| --- | --- | --- |
| `/status` | GET | 查看当前模式、自动交易开关与交易对。 / Bot status & symbols. |
| `/signals` | GET | 获取各交易对的模型信号。 / Model signals per symbol. |
| `/candles?symbol=BTC_USDT` | GET | 拉取K线数据。 / Candle data. |
| `/trades?limit=20` | GET | 最近成交记录。 / Recent trades. |
| `/cycle` | POST | 执行一次分析/下单流程。 / Run one decision cycle. |
| `/train?symbol=BTC_USDT&device=auto&epochs=30` | POST | 混合训练并更新在线模型参数。 / Hybrid training. |
| `/auto-trade/enable` | POST | 开启自动交易。 / Enable auto-trade. |
| `/auto-trade/disable` | POST | 关闭自动交易。 / Disable auto-trade. |

## 常见问题 / FAQ
### 为什么配置了 API 也无法下单？
- 请确认 `ENABLE_AUTO_TRADE=true`，否则执行流程会被跳过。  
  Ensure `ENABLE_AUTO_TRADE=true`, otherwise orders are skipped.
- 如果 `TRADING_MODE=paper` 且 `ENABLE_PAPER_TRADE=true`，系统只会走测试网。  
  When `TRADING_MODE=paper`, the bot uses testnet (`PAPER_API_*`) only.
