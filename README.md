# newschannelpolymonitor

监控 Telegram 新闻频道，自动匹配 Polymarket 相关预测市场，并推送到目标频道。

## 功能

- 定期抓取指定 Telegram 公开频道（默认：深潮 TechFlowDaily）的最新消息
- 提取新闻标题，自动搜索 Polymarket 相关市场
- 按交易量从高到低排序，推送格式化消息到目标 Telegram 频道

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SOURCE_URL` | 监控的 Telegram 频道 URL | `https://t.me/s/TechFlowDaily` |
| `TARGET_CHAT_ID` | 推送目标频道 ID | `-1003713216091` |
| `TG_BOT_TOKEN` | Telegram Bot Token（必填） | 无 |
| `POLL_SECONDS` | 轮询间隔（秒） | `20` |
| `STATE_PATH` | 状态文件路径 | `/root/.openclaw/workspace/.tg_poly_web_state.json` |
| `MAX_MARKETS` | 每条新闻最多展示的市场数 | `3` |

## 依赖

- Python 3.8+
- [`polymarket` CLI](https://github.com/polymarket/cli)（需在 PATH 中可用）

## 使用

```bash
# 设置环境变量
export TG_BOT_TOKEN="your_bot_token"
export TARGET_CHAT_ID="your_channel_id"

# 运行
python telegram_polymarket_monitor_web.py
```

## 推送格式

```
*深潮新闻：[新闻标题]*

相关 Polymarket
- [市场问题](https://polymarket.com/market/slug) ($1,234,567)
- [市场问题](https://polymarket.com/market/slug) ($567,890)
```
