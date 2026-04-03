"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    QUANDBACK PRO - STRATEGY CONFIGURATION                      ║
║                   Generic Backtesting & Strategy Analysis System               ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ══════════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
TRADE_LOG_DIR = BASE_DIR / "trade_logs"

# Create directories
LOG_DIR.mkdir(exist_ok=True)
TRADE_LOG_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════
# TRADING PARAMETERS
# ══════════════════════════════════════════════════════════════════════════

# Symbol Configuration (Spot and Futures)
SYMBOL_CONFIG = {
    # NIFTY
    "NIFTY_SPOT": {
        "symbol": "NIFTY SPOT",
        "exchange": "NSE",
        "lot_size": 50,
        "tick_size": 0.05,
        "orb_duration": 15,
        "target": 50,
        "sl": 30,
        "volume_confirm": 2.0,
        "type": "SPOT",
    },
    "NIFTY_FUT": {
        "symbol": "NIFTY FUT",
        "exchange": "NSE",
        "lot_size": 50,
        "tick_size": 0.05,
        "orb_duration": 15,
        "target": 50,
        "sl": 30,
        "volume_confirm": 2.0,
        "type": "FUTURES",
    },
    # BANKNIFTY
    "BANKNIFTY_SPOT": {
        "symbol": "BANKNIFTY SPOT",
        "exchange": "NSE",
        "lot_size": 15,
        "tick_size": 0.05,
        "orb_duration": 10,
        "target": 100,
        "sl": 50,
        "volume_confirm": 2.0,
        "type": "SPOT",
    },
    "BANKNIFTY_FUT": {
        "symbol": "BANKNIFTY FUT",
        "exchange": "NSE",
        "lot_size": 15,
        "tick_size": 0.05,
        "orb_duration": 10,
        "target": 100,
        "sl": 50,
        "volume_confirm": 2.0,
        "type": "FUTURES",
    },
}

# Default symbol
DEFAULT_SYMBOL = "NIFTY_FUT"

# ══════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

CAPITAL = 1000000  # Rs 10 lakh
RISK_PER_TRADE_PCT = 0.02  # 2% of capital
MAX_POSITIONS = 1  # Maximum concurrent positions
MAX_DAILY_TRADES = 2  # Max trades per day
MAX_DAILY_LOSS_PCT = 0.05  # Stop trading if 5% daily loss
MAX_SLIPPAGE_PCT = 0.0005  # 0.05%

# ══════════════════════════════════════════════════════════════════════════
# TRADING HOURS
# ══════════════════════════════════════════════════════════════════════════

MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
ENTRY_DEADLINE = "14:00"  # No new entries after 2 PM
SQUARE_OFF_TIME = "15:15"  # Force exit all positions

# ══════════════════════════════════════════════════════════════════════════
# TRADING COSTS
# ══════════════════════════════════════════════════════════════════════════

BROKERAGE_PER_ORDER = 20  # Rs
STT_BUY_RATE = 0.0
STT_SELL_RATE = 0.00025  # 0.025% on sell
TRANSACTION_CHARGE_PER_CRORE = 1.7  # Rs per crore turnover
GST_RATE = 0.18  # 18%
STAMP_DUTY_RATE = 0.00002  # 0.002%

# ══════════════════════════════════════════════════════════════════════════
# API CONFIGURATION (SET YOUR CREDENTIALS)
# ══════════════════════════════════════════════════════════════════════════

# Kite Connect (Zerodha)
KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_REQUEST_TOKEN = os.getenv("KITE_REQUEST_TOKEN", "")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")

# AliceBlue
ALICEBLUE_USER_ID = os.getenv("ALICEBLUE_USER_ID", "")
ALICEBLUE_API_KEY = os.getenv("ALICEBLUE_API_KEY", "")
ALICEBLUE_API_SECRET = os.getenv("ALICEBLUE_API_SECRET", "")

# Shoonya
SHOONYA_USER_ID = os.getenv("SHOONYA_USER_ID", "")
SHOONYA_PASSWORD = os.getenv("SHOONYA_PASSWORD", "")
SHOONYA_API_KEY = os.getenv("SHOONYA_API_KEY", "")
SHOONYA_API_SECRET = os.getenv("SHOONYA_API_SECRET", "")

# ══════════════════════════════════════════════════════════════════════════
# TELEGRAM ALERTS (OPTIONAL)
# ══════════════════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ══════════════════════════════════════════════════════════════════════════
# WEBHOOK SERVER
# ══════════════════════════════════════════════════════════════════════════

WEBHOOK_HOST = "0.0.0.0"
WEBHOOK_PORT = 8080
WEBHOOK_PATH = "/orb_signal"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your_secret_key_here")

# ══════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════

LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ══════════════════════════════════════════════════════════════════════════
# TRADING FLAGS
# ══════════════════════════════════════════════════════════════════════════

ENABLE_AUTO_TRADING = False  # Set to True after testing
ENABLE_TELEGRAM_ALERTS = False
ENABLE_TRAIL_SL = True  # Trailing stop loss
TRAIL_SL_POINTS = 15  # Trail SL after 15 points profit
TRAIL_SL_DISTANCE = 20  # Keep SL 20 points behind price

# ══════════════════════════════════════════════════════════════════════════
# INSTRUMENT TOKENS (KITE)
# ══════════════════════════════════════════════════════════════════════════

# Current month futures tokens (update monthly)
KITE_TOKENS = {
    "NIFTY": 256265,  # Update with current month token
    "BANKNIFTY": 260105,  # Update with current month token
    "FINNIFTY": 322509,  # Update with current month token
}


def get_symbol_config(symbol: str = None) -> dict:
    """Get configuration for a symbol"""
    if symbol is None:
        symbol = DEFAULT_SYMBOL
    symbol = symbol.upper()
    return SYMBOL_CONFIG.get(symbol, SYMBOL_CONFIG[DEFAULT_SYMBOL])


def validate_config() -> bool:
    """Validate required configuration"""
    errors = []

    if ENABLE_AUTO_TRADING:
        if not (KITE_API_KEY and KITE_ACCESS_TOKEN):
            if not (ALICEBLUE_API_KEY and ALICEBLUE_API_SECRET):
                if not (SHOONYA_API_KEY and SHOONYA_API_SECRET):
                    errors.append("No broker API credentials found")

    if ENABLE_TELEGRAM_ALERTS:
        if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
            errors.append("Telegram credentials not configured")

    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"   - {error}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 20 + "ORB CONFIGURATION")
    print("=" * 70)

    print("\n📊 Symbol Configuration:")
    for symbol, config in SYMBOL_CONFIG.items():
        print(f"\n   {symbol}:")
        print(f"      Lot Size: {config['lot_size']}")
        print(f"      Target: {config['target']} pts")
        print(f"      SL: {config['sl']} pts")

    print(f"\n⚙️  Risk Management:")
    print(f"      Capital: Rs {CAPITAL:,.0f}")
    print(f"      Risk/Trade: {RISK_PER_TRADE_PCT*100}%")
    print(f"      Max Positions: {MAX_POSITIONS}")
    print(f"      Max Daily Trades: {MAX_DAILY_TRADES}")

    print(f"\n⏰ Trading Hours:")
    print(f"      Market Open: {MARKET_OPEN}")
    print(f"      Entry Deadline: {ENTRY_DEADLINE}")
    print(f"      Square Off: {SQUARE_OFF_TIME}")

    print(f"\n🤖 Auto Trading: {'ENABLED' if ENABLE_AUTO_TRADING else 'DISABLED'}")
    print(f"📱 Telegram Alerts: {'ENABLED' if ENABLE_TELEGRAM_ALERTS else 'DISABLED'}")

    print("\n" + "=" * 70)

    if validate_config():
        print("✅ Configuration Valid")
    else:
        print("⚠️  Fix errors before enabling auto-trading")

    print("=" * 70)
