# ORB Auto-Trade System - Complete Guide

## 📁 Project Structure

```
ORB_Strategy/
├── 📜 CONFIG FILES
│   ├── config.py              # Main configuration
│   ├── .env.example           # Environment template
│   └── requirements.txt       # Python dependencies
│
├── 🤖 CORE SYSTEM
│   ├── trading_engine.py      # Trading engine (positions, orders)
│   ├── webhook_server.py      # TradingView webhook receiver
│   └── start.py               # Quick start menu
│
├── 📊 TRADINGVIEW
│   ├── ORB_Strategy_Webhook.pine   # Pine script with webhook output
│   └── ORB_Strategy_PineScript.txt # Original script
│
├── 🧪 BACKTESTS
│   ├── orb_10year_backtest.py
│   ├── orb_optimized_backtest.py
│   ├── orb_robust_backtest.py
│   └── orb_breakout_backtest.py
│
└── 📖 DOCUMENTATION
    ├── ORB_README.md          # Strategy explanation
    ├── SETUP_GUIDE.md         # Setup instructions
    └── AUTO_TRADE_README.md   # This file
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
cd ORB_Strategy
pip install -r requirements.txt
```

### Step 2: Configure

```bash
# Copy env template
cp .env.example .env

# Edit .env with your credentials
# Or edit config.py directly
```

### Step 3: Start

```bash
python start.py
# Choose option 1 to start webhook server
```

---

## 📡 How It Works

```
┌─────────────────┐     Webhook      ┌─────────────────┐
│  TradingView    │ ────────────────► │  Flask Server   │
│  (Pine Script)  │                  │  (webhook_server)│
└─────────────────┘                  └────────┬────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │ Trading Engine  │
                                      │ (Position Mgmt) │
                                      └────────┬────────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         ▼                     ▼                     ▼
                  ┌──────────┐          ┌──────────┐          ┌──────────┐
                  │ Kite API │          │Telegram  │          │  Trade   │
                  │(Zerodha) │          │ Alerts   │          │   Log    │
                  └──────────┘          └──────────┘          └──────────┘
```

---

## ⚙️ Configuration Options

### Auto Trading Flags

```python
# In config.py
ENABLE_AUTO_TRADING = False  # Set True after testing
ENABLE_TELEGRAM_ALERTS = False
ENABLE_TRAIL_SL = True
```

### Risk Management

```python
CAPITAL = 1000000  # Rs 10 lakh
RISK_PER_TRADE_PCT = 0.02  # 2% per trade
MAX_POSITIONS = 1
MAX_DAILY_TRADES = 2
MAX_DAILY_LOSS_PCT = 0.05  # Stop at 5% daily loss
```

---

## 📱 Setting Up TradingView Alerts

### Alert Configuration

1. Open `ORB_Strategy_Webhook.pine` in TradingView
2. Add to chart
3. Create Alert with:
   - **Condition**: `ORB Entry Signal`
   - **Webhook URL**: `http://YOUR_IP:8080/orb_signal`
   - **Message**: Use default template

### Alert Message Format

```
{{ticker}}, {{time}}, {{close}}, {{plot_orb_high}}, {{plot_orb_low}}, {{plot_volume_ratio}}, {{strategy.order.action}}
```

Example output:
```
NIFTY, 0935, 22450.00, 22470.00, 22430.00, 2.5, LONG
```

---

## 🧪 Testing

### 1. Test Webhook (without TradingView)

```bash
curl -X POST http://localhost:8080/orb_signal \
  -H "Content-Type: application/json" \
  -d '{"text": "NIFTY, 0935, 22450.00, 22470.00, 22430.00, 2.5, LONG"}'
```

### 2. Test with Paper Trading

1. Set `ENABLE_AUTO_TRADING = False` in config.py
2. Run `python start.py`
3. Trigger TradingView alerts
4. Check logs in `logs/trading_YYYYMMDD.log`

### 3. Test APIs

```bash
python start.py
# Choose option 2 (Test Configuration)
```

---

## 📊 Monitoring

### Web Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check |
| `/status` | Trading summary |
| `/positions` | Open positions |
| `/trades` | Trade history |

### Example

```bash
curl http://localhost:8080/status
```

Response:
```json
{
  "summary": {
    "date": "2026-04-03",
    "trades": 2,
    "winning": 1,
    "losing": 1,
    "pnl": 2500.50,
    "win_rate": 50.0
  },
  "positions": []
}
```

---

## 🔧 Troubleshooting

### Issue: Webhook not receiving signals

**Solution:**
1. Check if server is running: `curl http://localhost:8080/health`
2. Verify TradingView webhook URL
3. Check firewall settings
4. If using ngrok, ensure it's running

### Issue: Orders not placing

**Solution:**
1. Verify API credentials in config.py
2. Check `ENABLE_AUTO_TRADING = True`
3. Verify Kite tokens are current
4. Check broker account has margin

### Issue: Telegram alerts not working

**Solution:**
1. Verify bot token and chat ID
2. Start bot with /start command
3. Check `ENABLE_TELEGRAM_ALERTS = True`

---

## 📈 Daily Workflow

### Pre-Market (9:00 AM)

```bash
# 1. Start the system
python start.py
# Option 1 → Start Webhook Server

# 2. Verify status
curl http://localhost:8080/status

# 3. Check previous day trades
# View logs/trading_YYYYMMDD.log
```

### During Market Hours

- Monitor Telegram alerts
- Check /status periodically
- Be ready for manual intervention

### Post-Market (3:30 PM)

```bash
# 1. Check final status
curl http://localhost:8080/trades

# 2. Review P&L
# View trade_logs/trades_YYYYMMDD.csv
```

---

## ⚠️ Important Safety Notes

1. **Start with paper trading** - Test thoroughly
2. **Set loss limits** - Configure MAX_DAILY_LOSS_PCT
3. **Keep manual override** - Know how to close positions manually
4. **Monitor daily** - Don't set and forget
5. **Check costs** - Brokerage and STT affect net profits

---

## 📞 Next Steps

1. **Read** `SETUP_GUIDE.md` for detailed setup
2. **Review** `ORB_README.md` for strategy details
3. **Test** with paper trading first
4. **Deploy** to VPS for 24/7 operation
5. **Monitor** daily P&L and adjust parameters

---

## 📄 License

For educational purposes. Use at your own risk. Trading involves substantial risk of loss.

---

**Last Updated**: 2026-04-03
**Version**: 1.0
