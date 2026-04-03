"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                   ORB AUTO-TRADE EXECUTION SYSTEM                                     ║
║                                                                               ║
║  • Real-time signal detection                                               ║
║  • Order management                                                       ║
║  • Position tracking                                                    ║
║  • Risk management                                                     ║
║  • Trade logging                                                        ║
║                                                                               ║
║  API INTEGRATION:                                                         ║
║  • Kite Connect / Zero API                                               ║
║  • AliceBlue / Shoony / Zerodha                                              ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

SYMBOL = "NIFTY FUT"
EXCHANGE = "NSE"
LOT_SIZE = 50
QTY_PER_TRADE = 1  # Start with 1 lot, scale to 2-3 lots

# ORB Parameters
ORB_DURATION = 15  # minutes
VOLUME_CONFIRM = 2.0  # volume ratio
TARGET_POINTS = 50
SL_POINTS = 30

# Risk Management
MAX_POSITIONS = 1  # Maximum concurrent positions
MAX_DAILY_TRADES = 2  # Max trades per day
CAPITAL = 1000000  # Rs 10 lakh
MAX_SLIPPAGE_PCT = 0.0005  # 0.05%

# Trading Hours
TRADING_START_HOUR = 9
TRADING_END_HOUR = 15
ENTRY_DEADLINE = 14  # No new entries after 2 PM

# Costs
BROKERAGE_PER_ORDER = 20
STT_RATE = 0.0001  # 0.01% on sell
TRANSACTION_CHARGE_PER_CRORE = 1.7  # Rs 1.7 per crore
GST_RATE = 0.18  # 18%

print("=" * 100)
print(" " " * 25 + "ORB AUTO-TRADE EXECUTION SYSTEM")
print("=" * 100)

# ══════════════════════════════════════════════════════════════════════
# ORDER MANAGEMENT SYSTEM
# ═════════════════════════════════════════════════════════════════════════

class OrderManager:
    """Manages orders, positions, trades"""

    def __init__(self):
        self.positions = {}  # trade_id → position info
        self.trades = []  # List of all trades
        self.trade_count = 0
        self.realized_pnl = 0

    def calculate_slippage(self, entry, direction):
        """Calculate slippage in points"""
        slippage = (entry / 100) * MAX_SLIPPAGE_PCT * LOT_SIZE
        return slippage / LOT_SIZE

    def calculate_charges(self, entry, exit_price, qty):
        """Calculate trading costs in points"""
        turnover = (entry + exit_price) * qty
        brokerage = BROKERAGE_PER_ORDER * 2
        stt = exit_price * qty * STT_RATE
        transaction = (turnover / 10000000) * TRANSACTION_CHARGE_PER_CRORE * 2
        gst = (brokerage + transaction) * GST_RATE
        stamp = entry * qty * 0.00002  # Stamp duty

        total_cost_rs = brokerage + stt + transaction + gst + stamp
        cost_points = total_cost_rs / qty

        # Add slippage
        slippage_points = self.calculate_slippage(entry if direction == 1 else exit_price, direction)
        return cost_points + slippage_points

    def place_order(self, direction, price, qty):
        """Simulated order placement"""
        print(f"    [ORDER] {direction} {qty} lots @ {price:.2f}")
        order_id = f"TRD{self.trade_count:05d}"

        # Position tracking
        self.positions[order_id] = {
            'direction': direction,
            'entry_price': price,
            'qty': qty,
            'entry_time': datetime.now(),
            'status': 'OPEN',
            'sl_price': price - SL_POINTS if direction == 1 else price + SL_POINTS,
            'target_price': price + TARGET_POINTS if direction == 1 else price - TARGET_POINTS
        }

        self.trade_count += 1
        return order_id

    def exit_position(self, order_id, exit_price, exit_reason):
        """Exit a position"""
        if order_id in self.positions:
            pos = self.positions[order_id]
            entry = pos['entry_price']
            direction = pos['direction']
            qty = pos['qty']

            costs = self.calculate_charges(entry, exit_price, qty)
            gross_pnl = (exit_price - entry_price) if direction == 1 else (entry - exit_price)
            net_pnl = gross_pnl - costs

            # Update realized P&L
            self.realized_pnl += net_pnl

            # Record trade
            self.trades.append({
                'trade_id': order_id,
                'direction': direction,
                'entry': entry,
                'exit': exit_price,
                'qty': qty,
                'entry_time': pos['entry_time'],
                'exit_time': datetime.now(),
                'reason': exit_reason,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'costs': costs,
                'status': 'CLOSED'
            })

            # Remove from positions
            del self.positions[order_id]

            print(f"    [EXIT] {direction} @ {exit_price:.2f} | Reason: {exit_reason} | P&L: Rs.{net_pnl*qty:,.0f}")

    def get_signal(self):
        """Main signal detection logic"""
        # This would connect to TradingView or similar
        # Returns: (direction, entry_price, confidence) or (None, None, 0)

        # Placeholder - integration point
        # In production, this would fetch real-time data and apply ORB logic

        # For now, return None - signal must come from external signal
        return None, None, 0

    def get_position_size(self):
        """Get current position size based on account and risk"""
        # Position sizing: 1-3% of capital per trade
        capital_at_risk = CAPITAL * 0.02  # 2% risk per trade
        qty = int(capital_at_risk / LOT_SIZE)
        return max(1, min(3, qty))

# ════════════════════════════════════════════════════════════════════
# SIGNAL LOGIC (PLACEHOLDER FOR TRADINGVIEW/ALICEBLUE INTEGRATION)
# ══════════════════════════════════════════════════════════════

def get_orb_signal_data():
    """
    Fetch ORB signal from TradingView chart or external source
    Returns: {
        'direction': 'LONG' or 'SHORT',
        'entry_price': price,
        'orb_high': ORB high level,
        'orb_low': ORB low level,
        'volume_ratio': volume / MA volume,
        'confidence': 0-100
    }
    """
    # This would fetch real-time data and apply ORB logic
    # For now, return None
    return None


# ════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION LOOP (PLACEHOLDER)
# ══════════════════════════════════════════════════════════════

class ORBTrader:
    """Main trading system"""

    def __init__(self):
        self.order_manager = OrderManager()
        self.active = True

    def run(self):
        """Main trading loop"""
        print("\n" + "=" * 100)
        print(" " " * 30 + "ORB AUTO-TRADER STARTED")
        print("=" * 100)
        print("\n[SYSTEM] Ready to trade")
        print("[INFO] Waiting for signals from TradingView or other source...")
        print("\n[INFO] Running 9:15 AM to 2:00 PM")
        print("       Risk: 2% per trade")
        print("       Max positions: 1")
        print("       Position size: Dynamic (1-3 lots based on capital)")
        print("\n" + "=" * 100)

        # Wait for signals (placeholder - in production, this would connect to TV)
        print("\n[INFO] In production, this would:")
        print("  1. Fetch real-time data")
        print("   2. Apply ORB logic")
        print("  3. Check market conditions")
        print("  4. Place order via API")
        print("\n" + "=" * 100)

        # In production, this would run continuously
        print("\n[INFO] For now, signals must be generated from TradingView alerts")
        print("       See Pine Script for signal generation.")

    def process_signal(self, direction, entry_price, orb_high, orb_low, volume_ratio):
        """Process a trading signal"""
        # Check volume confirmation
        if volume_ratio < VOLUME_CONFIRM:
            print(f"    [SKIP] Volume too low: {volume_ratio:.2f}x (need >{VOLUME_CONFIRM}x)")
            return False

        # Check if trading allowed times
        current_time = datetime.now().hour
        if current_time < TRADING_START_HOUR or current_time >= TRADING_END_HOUR:
            print(f"    [SKIP] Outside trading hours: {current_time}:00")
            return False

        # Check max daily trades
        daily_trades = len([t for t in self.order_manager.trades if t['entry_time'].date() == datetime.now().date()])
        if daily_trades >= MAX_DAILY_TRADES:
            print(f"    [SKIP] Max daily trades reached: {daily_trades}")
            return False

        # Check capital
        if self.order_manager.realized_pnl < -CAPITAL * 0.1:  # 10% loss
            print(f"    [SKIP] Loss limit reached")
            return False

        # Place order
        qty = self.order_manager.get_position_size()
        order_id = self.order_manager.place_order(direction, entry_price, qty)

        # Set up trailing
        # In production, would manage exits here

        return True

# ════════════════════════════════════════════════════════════════════════
# REPORTING
# ════════════════════════════════════════════════════════════════════════

def generate_performance_report():
    """Generate trading report"""
    # In production, this would read from trade log
    print("\n" + "=" * 100)
    print(" " " * 30 + "TRADING PERFORMANCE REPORT")
    print("=" * 100)

    trades = []  # Placeholder - would read from log

    if trades:
        # Calculate metrics
        total = len(trades)
        winning = len([t for t in trades if t['net_pnl'] > 0])
        losing = len([t for t in trades if t['net_pnl'] < 0])

        gross_pnl = sum([t['gross_pnl'] for t in trades])
        net_pnl = sum([t['net_pnl'] for t in trades])

        print(f"\nTotal Trades: {total}")
        print(f"Winning Trades: {winning} ({winning/total*100:.1f}%)")
        print(f"Losing Trades: {losing} ({losing/total*100:.1f}%)")
        print(f"Gross P&L: {gross_pnl:.0f} points")
        print(f"Net P&L: {net_pnl:.0f} points")
        print(f"Net P&L (Rs): {net_pnl*LOT_SIZE:,.0f}")

        if winning_trades := [t for t in trades if t['net_pnl'] > 0]:
            avg_win = sum([t['net_pnl'] for t in winning_trades]) / len(winning_trades)
        else:
            avg_win = 0

        if losing_trades := [t for t in trades if t['net_pnl'] < 0]:
            avg_loss = sum([t['net_pnl'] for t in losing_trades]) / len(losing_trades)
        else:
            avg_loss = 0

        print(f"Avg Win: {avg_win:.0f} points")
        print(f"Avg Loss: {avg_loss:.0f} points")
        print(f"Profit Factor: {abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}")

        # Save trade log
        log_path = Path(OUTPUT_DIR) / "trade_log.csv"
        pd.DataFrame(trades).to_csv(log_path, index=False)
        print(f"Trade log saved to: {log_path}")

    print("\n" + "=" * 100)


# ══════════════════════════════════════════════════════════════════════════
# API INTEGRATION TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

"""
API INTEGRATION EXAMPLE (Kite/Zero):

```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="your_key", secret="your_secret")
kite.connect()

def fetch_nifty_data():
    # Get OHLC data
    ohlc = kite.ohlc("NIFTYFUT", "minute")
    return ohlc

def place_kite_order(direction, quantity):
    if direction == "LONG":
        kite.put_order("NIFTYFUT", "BUY", quantity=quantity)
    else:
        kite.put_order("NIFTYFUT", "SELL", quantity=quantity)
```

// FOR ALICEBLUE:
```pine
// Send alerts to your Telegram bot
alert("ORB Signal: " + direction)
```

// FOR ZERODHA:
```pine
// Send orders via WebSocket
// Connect to your broker API
```
"""

print("\n" + "=" * 100)
print("AUTO-TRADE SYSTEM READY")
print("=" * 100)
print("\nTo use:")
print("1. Signals from TradingView → Auto-trade via API")
print("2. ORB Strategy → Entry signals → Auto-trade via API")
print("3. For now, this is a framework - actual API integration needed")
print("\n" + "=" * 100)
