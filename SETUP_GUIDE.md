# ORB Auto-Trade System - Setup Guide

## Overview

Complete auto-trade execution system for ORB strategy with:
- TradingView webhook integration
- Kite Connect / AliceBlue / Shoonya API support
- Real-time position management
- Telegram alerts
- Trade logging and reporting

---

## 📋 Prerequisites

1. Python 3.9 or higher
2. TradingView Pro/Pro+ account (for webhooks)
3. Broker account with API access (Kite/AliceBlue/Shoonya)
4. Server/VPS with public IP (for webhooks) OR local ngrok

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ORB_Strategy
pip install -r requirements.txt
```

### 2. Configure Settings

Edit `config.py` or create `.env` file:

```bash
# .env file
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

WEBHOOK_SECRET=your_secret_key
```

### 3. Test Configuration

```bash
python config.py
```

Should show: ✅ Configuration Valid

### 4. Start Webhook Server

```bash
python webhook_server.py
```

Output:
```
══════════════════════════════════════════════════════════════════
            TRADINGVIEW WEBHOOK SERVER
══════════════════════════════════════════════════════════════════

🚀 Server starting...
   Port: 8080
   Endpoint: http://localhost:8080/orb_signal

⚙️  Configuration:
   Auto Trading: 🔴 DISABLED
   Telegram Alerts: 🔴 DISABLED

✅ Server Ready! Waiting for signals...
```

---

## 📡 TradingView Setup

### Option 1: Webhook Alerts

1. Open your ORB Pine Script in TradingView
2. Click "Add to Chart"
3. Click "Alert" button (top right)
4. Configure alert:

**Condition:**
```
ORB Entry Signal
```

**Webhook URL:**
```
http://YOUR_SERVER_IP:8080/orb_signal
```

**Message:**
```
{{ticker}}, {{time}}, {{close}}, {{plot_orb_high}}, {{plot_orb_low}}, {{plot_volume_ratio}}, {{strategy.order.action}}
```

### Option 2: Use Provided Pine Script

Use `ORB_Strategy_Webhook.pine` which has built-in webhook formatting.

---

## 🔐 Broker API Setup

### Kite Connect (Zerodha)

1. Get API credentials: https://developers.kite.trade/
2. Generate access token:
```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key="your_key")
print(kite.login_url())
# Visit URL, get request_token, then:
print(kite.generate_session("request_token", "api_secret"))
```

### AliceBlue

1. Enable API from AliceBlue dashboard
2. Get API Key and Secret
3. Update in config.py

### Shoonya

1. Download API credentials from Shoonya dashboard
2. Update in config.py

---

## 📱 Telegram Alerts Setup

1. Create bot via @BotFather
2. Get bot token
3. Get chat ID (send message to bot, visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`)
4. Update in config.py

---

## 🌐 Expose Webhook (Local Development)

### Using ngrok

```bash
# Install ngrok
# Download from https://ngrok.com/

# Run ngrok
ngrok http 8080

# Use the https URL in TradingView
# Example: https://abc123.ngrok.io/orb_signal
```

### Production Deployment

1. Use VPS (AWS/DigitalOcean/Azure)
2. Set up firewall rules
3. Use nginx as reverse proxy (recommended)
4. Enable SSL with Let's Encrypt

---

## 📊 File Structure

```
ORB_Strategy/
├── config.py                  # Configuration settings
├── trading_engine.py          # Core trading logic
├── webhook_server.py          # Flask webhook server
├── ORB_Strategy_Webhook.pine  # TradingView script
├── requirements.txt           # Python dependencies
├── logs/                      # Trading logs
│   └── trading_YYYYMMDD.log
├── trade_logs/                # Trade CSV files
│   └── trades_YYYYMMDD.csv
└── SETUP_GUIDE.md            # This file
```

---

## 🎯 Testing

### 1. Test Webhook Server

```bash
curl -X POST http://localhost:8080/orb_signal \
  -H "Content-Type: application/json" \
  -d '{"text": "NIFTY, 0935, 22450.00, 22470.00, 22430.00, 2.5, LONG"}'
```

Expected response:
```json
{
  "status": "success",
  "message": "Order placed"
}
```

### 2. Test Configuration

```bash
python trading_engine.py
```

### 3. Paper Trading Mode

Before enabling real trading:
1. Set `ENABLE_AUTO_TRADING = False` in config.py
2. Test with TradingView alerts
3. Monitor logs in `logs/` folder
4. Verify trades in `trade_logs/`

---

## ⚠️ Risk Warnings

1. **Start with paper trading** - Test thoroughly before real money
2. **Monitor daily** - Check positions and P&L regularly
3. **Set loss limits** - Configure `MAX_DAILY_LOSS_PCT`
4. **Keep manual override** - Always be able to close positions manually
5. **Check costs** - Brokerage, STT, slippage affect net profits

---

## 🔧 Troubleshooting

### Webhook not receiving signals
- Check firewall settings
- Verify ngrok is running (if local)
- Check TradingView webhook URL is correct
- Look at server logs

### Orders not placing
- Check API credentials
- Verify `ENABLE_AUTO_TRADING = True`
- Check Kite tokens are current
- Verify broker account has margin

### Telegram alerts not working
- Verify bot token and chat ID
- Bot must be started with /start
- Check chat ID is correct (not channel ID)

---

## 📈 Monitoring

### Check Status

```bash
curl http://localhost:8080/status
```

### View Positions

```bash
curl http://localhost:8080/positions
```

### View Trades

```bash
curl http://localhost:8080/trades
```

---

## 🔄 Daily Operations

**Before Market Open (9:00 AM)**
1. Check server is running
2. Verify API connection
3. Check capital and margins
4. Review previous day trades

**During Market Hours (9:15 AM - 3:30 PM)**
1. Monitor Telegram alerts
2. Check /status endpoint periodically
3. Be ready for manual intervention

**After Market Close (3:30 PM)**
1. Verify all positions closed
2. Review trade logs
3. Calculate daily P&L
4. Plan for next day

---

## 📞 Support

For issues or questions:
1. Check logs in `logs/` folder
2. Review configuration in `config.py`
3. Verify broker API status
4. Check TradingView webhook status

---

## 📝 License

This system is for educational purposes. Use at your own risk.

---

## ✅ Checklist Before Going Live

- [ ] Tested with paper trading for at least 1 week
- [ ] Broker API credentials verified
- [ ] Webhook receiving signals correctly
- [ ] Telegram alerts working
- [ ] Loss limits configured
- [ ] Emergency exit plan known
- [ ] Server/VPS stable
- [ ] SSL certificate installed (production)
- [ ] Daily P&L tracking set up
- [ ] Backup plan for server failure
