# ORB Auto-Trade System - Railway Deployment Guide

## 🚀 Deploy to Railway in 10 Minutes

### Prerequisites

1. GitHub account
2. Railway account (sign up at railway.app)
3. Historical data files (optional, can upload later)

---

## 📋 Step-by-Step Deployment

### Step 1: Push Code to GitHub

```bash
cd C:/Users/elamuruganm/Documents/Projects/Strategy/ORB_Strategy

# Initialize git if not already
git init

# Add all files
git add .

# Commit
git commit -m "ORB Auto-Trade System - Railway Ready"

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/orb-auto-trade.git
git branch -M main
git push -u origin main
```

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Select your `orb-auto-trade` repository

### Step 3: Configure Services

Railway will automatically detect the Python service. You need to add a database:

1. Click **New Service**
2. Select **Database**
3. Choose **PostgreSQL**
4. Railway will add it to your project

### Step 4: Set Environment Variables

Go to your service → **Variables** tab and add:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Auto-filled by Railway (see below) |
| `SECRET_KEY` | Generate a random string |
| `ENABLE_AUTO_TRADING` | `False` (start with paper trading) |
| `PORT` | `8080` |

**To get DATABASE_URL:**
1. Click on your PostgreSQL service
2. Go to **Variables** tab
3. Copy the `DATABASE_URL` value
4. Paste it in your app's variables

### Step 5: Deploy!

1. Click **Deploy** button
2. Wait for build to complete (~2-3 minutes)
3. Get your app URL from Railway dashboard

---

## 🌐 After Deployment

### Access Your App

Railway will provide a URL like: `https://orb-auto-trade.up.railway.app`

Visit it to see your dashboard!

### Upload Historical Data

1. Go to **Data** page
2. Upload CSV files with columns: `date, time, open, high, low, close, volume`

**Free Data Sources:**
- [NSE Bhavcopy](https://www.nseindia.com/products-content/equities-market-archives)
- [Yahoo Finance](https://in.finance.yahoo.com)
- [Indian Intraday Historical](https://historicaldata.indianintraday.in/)

### Run Your First Backtest

1. Go to **Backtests** → **New Backtest**
2. Select parameters
3. Click **Run Backtest**

---

## 🔗 Setup TradingView Webhook

1. Open TradingView
2. Load `ORB_Strategy_Webhook.pine`
3. Create Alert with:
   - **Webhook URL**: `https://YOUR_APP.railway.app/api/orb_signal`
   - **Message**: Use template in Pine Script

---

## 📊 Railway Services Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RAILWAY PROJECT                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   Flask App     │────────▶│   PostgreSQL    │           │
│  │   (Python)      │         │   Database      │           │
│  └─────────────────┘         └─────────────────┘           │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────┐                                       │
│  │   Public URL    │                                       │
│  │   (Auto-generated)                                      │
│  └─────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 Railway Pricing (Free Tier)

| Resource | Free Tier | Paid (from $5/month) |
|----------|-----------|---------------------|
| Hours | 500 hours/month | Unlimited |
| RAM | 512 MB | 1 GB+ |
| CPU | Shared | Dedicated |
| Database | 1 GB | 10 GB+ |

**Free tier is sufficient for:**
- Development
- Paper trading
- Occasional backtests
- Low-volume webhook handling

---

## 🛠️ Managing Your Deployment

### View Logs

```bash
# Using Railway CLI
railway logs

# Or in dashboard: Service → Logs tab
```

### Restart Service

```bash
railway up
# Or click "Redeploy" in dashboard
```

### Access Database

```bash
# Connect to PostgreSQL
railway db

# Or get connection string from dashboard
```

### Update Code

```bash
git add .
git commit -m "Update"
git push

# Railway auto-deploys on push
```

---

## 🔒 Security Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Keep `ENABLE_AUTO_TRADING = False` until tested
- [ ] Use Railway's domain (SSL included)
- [ ] Set up monitoring alerts in Railway
- [ ] Never commit API keys to Git

---

## 📈 Monitoring

### Railway Dashboard Features

- **Logs**: Real-time application logs
- **Metrics**: CPU, Memory, Network usage
- **Deployments**: Build history and status
- **Cron Jobs**: Scheduled tasks (optional)

### Health Check

Your app has `/health` endpoint that Railway monitors.

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Check build logs in Railway dashboard
# Common issues:
# - Missing dependencies → update requirements.txt
# - Python version mismatch → ensure 3.9+
```

### Database Connection Error

```bash
# Ensure DATABASE_URL is set correctly
# Format: postgresql://user:pass@host:port/dbname
```

### Webhook Not Working

```bash
# Check logs: railway logs --tail
# Verify TradingView URL is correct
# Test webhook: curl -X POST YOUR_URL/api/orb_signal -d '{"text":"test"}'
```

---

## 📦 What's Included

Your Railway deployment includes:

| Feature | Description |
|---------|-------------|
| **Web UI** | Dashboard for trades, backtests, data |
| **REST API** | Webhook endpoint, status, trades |
| **PostgreSQL** | Persistent database for all data |
| **Backtesting** | Run backtests from browser |
| **Data Upload** | Upload historical data via UI |
| **Signal Logging** | All TradingView signals logged |

---

## 🚀 Going Live

When ready for live trading:

1. **Set `ENABLE_AUTO_TRADING = True`** in variables
2. **Add broker API credentials** (Kite, AliceBlue, etc.)
3. **Start with 1 lot** minimum
4. **Monitor first few trades** closely
5. **Keep manual override** ready

---

## 📞 Support

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **GitHub Issues**: For code-specific issues

---

**Last Updated**: 2026-04-03
**Version**: 1.0
