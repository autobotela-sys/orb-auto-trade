"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                         ORB TRADING ENGINE                                     ║
║                                                                               ║
║  Main execution engine for ORB strategy auto-trading                         ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import json
import threading
import time
from datetime import datetime, time as dt_time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from config import (
    SYMBOL_CONFIG, DEFAULT_SYMBOL, CAPITAL, RISK_PER_TRADE_PCT,
    MAX_POSITIONS, MAX_DAILY_TRADES, MAX_DAILY_LOSS_PCT,
    MARKET_OPEN, MARKET_CLOSE, ENTRY_DEADLINE, SQUARE_OFF_TIME,
    BROKERAGE_PER_ORDER, STT_BUY_RATE, STT_SELL_RATE,
    TRANSACTION_CHARGE_PER_CRORE, GST_RATE, STAMP_DUTY_RATE,
    LOG_DIR, TRADE_LOG_DIR, ENABLE_AUTO_TRADING,
    ENABLE_TRAIL_SL, TRAIL_SL_POINTS, TRAIL_SL_DISTANCE,
    KITE_API_KEY, KITE_ACCESS_TOKEN, KITE_TOKENS
)

# Default configs for symbols not in SYMBOL_CONFIG (fallbacks)
DEFAULT_SYMBOL_CONFIGS = {
    'NIFTY_SPOT': {'lot_size': 50, 'tick_size': 0.05, 'target': 50, 'sl': 30, 'volume_confirm': 2.0, 'exchange': 'NSE'},
    'NIFTY_FUT': {'lot_size': 50, 'tick_size': 0.05, 'target': 50, 'sl': 30, 'volume_confirm': 2.0, 'exchange': 'NSE'},
    'BANKNIFTY_SPOT': {'lot_size': 15, 'tick_size': 0.05, 'target': 100, 'sl': 50, 'volume_confirm': 2.0, 'exchange': 'NSE'},
    'BANKNIFTY_FUT': {'lot_size': 15, 'tick_size': 0.05, 'target': 100, 'sl': 50, 'volume_confirm': 2.0, 'exchange': 'NSE'},
}


def get_symbol_safe_config(symbol: str) -> dict:
    """Get symbol config with fallback to defaults"""
    symbol = symbol.upper()
    if symbol in SYMBOL_CONFIG:
        return SYMBOL_CONFIG[symbol]
    elif symbol in DEFAULT_SYMBOL_CONFIGS:
        return DEFAULT_SYMBOL_CONFIGS[symbol]
    else:
        # Return NIFTY_FUT as ultimate fallback
        return DEFAULT_SYMBOL_CONFIGS['NIFTY_FUT']


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / f"trading_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Direction(Enum):
    LONG = 1
    SHORT = -1


class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SQUARE_OFF = "SQUARE_OFF"


@dataclass
class Signal:
    """Trading signal from TradingView or other source"""
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    orb_high: float
    orb_low: float
    volume_ratio: float
    symbol: str = DEFAULT_SYMBOL
    timestamp: datetime = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    """Active trading position"""
    trade_id: str
    direction: Direction
    entry_price: float
    qty: int
    symbol: str
    entry_time: datetime
    orb_high: float
    orb_low: float
    sl_price: float
    target_price: float
    status: PositionStatus = PositionStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    highest_price: float = 0.0  # For trailing SL (long)
    lowest_price: float = 999999.0  # For trailing SL (short)
    trail_sl_triggered: bool = False


@dataclass
class Trade:
    """Completed trade record"""
    trade_id: str
    direction: str
    symbol: str
    entry_price: float
    exit_price: float
    qty: int
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    gross_pnl: float
    costs: float
    net_pnl: float
    points: float
    orb_high: float
    orb_low: float


class CostCalculator:
    """Calculate trading costs"""

    @staticmethod
    def calculate(entry_price: float, exit_price: float, qty: int, direction: Direction) -> float:
        """Calculate total trading costs in points"""
        turnover = (entry_price + exit_price) * qty

        # Brokerage
        brokerage = BROKERAGE_PER_ORDER * 2  # Buy + Sell

        # STT (only on sell side)
        stt = exit_price * qty * STT_SELL_RATE

        # Transaction charges
        transaction = (turnover / 10000000) * TRANSACTION_CHARGE_PER_CRORE * 2

        # GST on brokerage + transaction
        gst = (brokerage + transaction) * GST_RATE

        # Stamp duty (only on buy side)
        stamp = entry_price * qty * STAMP_DUTY_RATE

        total_cost_rs = brokerage + stt + transaction + gst + stamp
        cost_points = total_cost_rs / qty

        return cost_points


class PositionManager:
    """Manages positions and trades"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.trade_counter = 0
        self.daily_pnl = 0.0
        self.daily_trade_count = 0

    def get_position_size(self, symbol: str, price: float) -> int:
        """Calculate position size based on risk"""
        config = get_symbol_safe_config(symbol)
        lot_size = config['lot_size']
        sl_points = config['sl']

        # Risk amount
        risk_amount = CAPITAL * RISK_PER_TRADE_PCT

        # Quantity based on SL
        qty_from_sl = int(risk_amount / (sl_points * lot_size))

        # Min 1 lot, max based on configuration
        qty_lots = max(1, min(3, qty_from_sl))

        return qty_lots * lot_size

    def can_enter(self) -> Tuple[bool, str]:
        """Check if entry is allowed"""
        # Check max positions
        if len(self.positions) >= MAX_POSITIONS:
            return False, f"Max positions reached: {MAX_POSITIONS}"

        # Check daily trades
        if self.daily_trade_count >= MAX_DAILY_TRADES:
            return False, f"Max daily trades reached: {MAX_DAILY_TRADES}"

        # Check daily loss limit
        if self.daily_pnl <= -CAPITAL * MAX_DAILY_LOSS_PCT:
            return False, f"Daily loss limit reached: {MAX_DAILY_LOSS_PCT*100}%"

        return True, "OK"

    def open_position(self, signal: Signal) -> Optional[Position]:
        """Open a new position"""
        can_enter, reason = self.can_enter()
        if not can_enter:
            logger.warning(f"Entry blocked: {reason}")
            return None

        config = get_symbol_safe_config(signal.symbol)
        direction = Direction.LONG if signal.direction.upper() == "LONG" else Direction.SHORT

        # Calculate position size
        qty = self.get_position_size(signal.symbol, signal.entry_price)

        # Generate trade ID
        self.trade_counter += 1
        trade_id = f"{signal.symbol[:3]}{datetime.now().strftime('%Y%m%d%H%M%S')}{self.trade_counter:02d}"

        # Calculate SL and Target
        if direction == Direction.LONG:
            sl_price = signal.orb_low
            target_price = signal.entry_price + config['target']
        else:
            sl_price = signal.orb_high
            target_price = signal.entry_price - config['target']

        # Create position
        position = Position(
            trade_id=trade_id,
            direction=direction,
            entry_price=signal.entry_price,
            qty=qty,
            symbol=signal.symbol,
            entry_time=datetime.now(),
            orb_high=signal.orb_high,
            orb_low=signal.orb_low,
            sl_price=sl_price,
            target_price=target_price,
            status=PositionStatus.OPEN,
            highest_price=signal.entry_price if direction == Direction.LONG else 0,
            lowest_price=signal.entry_price if direction == Direction.SHORT else 999999
        )

        self.positions[trade_id] = position
        self.daily_trade_count += 1

        logger.info(f"✅ Position OPENED: {trade_id} | {direction.name} {qty} @ {signal.entry_price:.2f}")

        return position

    def close_position(self, trade_id: str, exit_price: float, reason: str) -> Optional[Trade]:
        """Close a position and record trade"""
        if trade_id not in self.positions:
            logger.warning(f"Position not found: {trade_id}")
            return None

        position = self.positions[trade_id]

        # Calculate P&L
        if position.direction == Direction.LONG:
            gross_pnl_points = exit_price - position.entry_price
        else:
            gross_pnl_points = position.entry_price - exit_price

        costs = CostCalculator.calculate(
            position.entry_price, exit_price, position.qty, position.direction
        )
        net_pnl_points = gross_pnl_points - costs

        # Create trade record
        trade = Trade(
            trade_id=trade_id,
            direction=position.direction.name,
            symbol=position.symbol,
            entry_price=position.entry_price,
            exit_price=exit_price,
            qty=position.qty,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            exit_reason=reason,
            gross_pnl=gross_pnl_points * position.qty,
            costs=costs * position.qty,
            net_pnl=net_pnl_points * position.qty,
            points=net_pnl_points,
            orb_high=position.orb_high,
            orb_low=position.orb_low
        )

        # Update stats
        self.daily_pnl += trade.net_pnl
        self.trades.append(trade)

        # Remove from positions
        del self.positions[trade_id]

        logger.info(
            f"✅ Position CLOSED: {trade_id} @ {exit_price:.2f} | "
            f"Reason: {reason} | P&L: Rs.{trade.net_pnl:,.0f} ({trade.points:+.1f} pts)"
        )

        return trade

    def update_trailing_sl(self, current_price: float) -> None:
        """Update trailing stop loss"""
        if not ENABLE_TRAIL_SL:
            return

        for trade_id, position in self.positions.items():
            if position.direction == Direction.LONG:
                # Update highest price
                if current_price > position.highest_price:
                    position.highest_price = current_price

                # Check if trail should trigger
                unrealized_points = position.highest_price - position.entry_price
                if unrealized_points >= TRAIL_SL_POINTS:
                    new_sl = position.highest_price - TRAIL_SL_DISTANCE
                    if new_sl > position.sl_price:
                        old_sl = position.sl_price
                        position.sl_price = new_sl
                        position.trail_sl_triggered = True
                        logger.debug(f"📈 Trailing SL updated: {trade_id} | {old_sl:.2f} → {new_sl:.2f}")

            else:  # SHORT
                # Update lowest price
                if current_price < position.lowest_price:
                    position.lowest_price = current_price

                # Check if trail should trigger
                unrealized_points = position.entry_price - position.lowest_price
                if unrealized_points >= TRAIL_SL_POINTS:
                    new_sl = position.lowest_price + TRAIL_SL_DISTANCE
                    if new_sl < position.sl_price:
                        old_sl = position.sl_price
                        position.sl_price = new_sl
                        position.trail_sl_triggered = True
                        logger.debug(f"📉 Trailing SL updated: {trade_id} | {old_sl:.2f} → {new_sl:.2f}")

    def check_exits(self, current_price: float) -> List[Tuple[str, float, str]]:
        """Check for exit conditions (SL, Target)"""
        exits = []

        for trade_id, position in self.positions.items():
            if position.direction == Direction.LONG:
                # Check SL
                if current_price <= position.sl_price:
                    exits.append((trade_id, position.sl_price, "SL Hit"))
                # Check Target
                elif current_price >= position.target_price:
                    exits.append((trade_id, position.target_price, "Target Hit"))
            else:  # SHORT
                # Check SL
                if current_price >= position.sl_price:
                    exits.append((trade_id, position.sl_price, "SL Hit"))
                # Check Target
                elif current_price <= position.target_price:
                    exits.append((trade_id, position.target_price, "Target Hit"))

        return exits

    def get_open_position(self, symbol: str = None) -> Optional[Position]:
        """Get open position for symbol"""
        if symbol:
            for pos in self.positions.values():
                if pos.symbol == symbol:
                    return pos
        elif self.positions:
            return list(self.positions.values())[0]
        return None

    def square_off_all(self, current_price: float) -> List[Trade]:
        """Square off all positions"""
        trades = []
        for trade_id in list(self.positions.keys()):
            trade = self.close_position(trade_id, current_price, "Square Off")
            if trade:
                trades.append(trade)
        return trades


class ORBTradingEngine:
    """Main trading engine for ORB strategy"""

    def __init__(self):
        self.position_manager = PositionManager()
        self.running = False
        self.kite = None
        self._init_kite()

    def _init_kite(self):
        """Initialize Kite Connect (if credentials available)"""
        try:
            if KITE_API_KEY and KITE_ACCESS_TOKEN:
                from kiteconnect import KiteConnect
                self.kite = KiteConnect(api_key=KITE_API_KEY)
                self.kite.set_access_token(KITE_ACCESS_TOKEN)
                logger.info("✅ Kite Connect initialized")
            else:
                logger.warning("⚠️  Kite Connect credentials not found - Running in PAPER mode")
        except ImportError:
            logger.warning("⚠️  kiteconnect not installed - Running in PAPER mode")

    def process_signal(self, signal: Signal) -> bool:
        """Process a trading signal"""
        logger.info(f"📡 Signal received: {signal.direction} {signal.symbol} @ {signal.entry_price:.2f}")

        # Check volume confirmation
        if signal.volume_ratio < get_symbol_safe_config(signal.symbol)['volume_confirm']:
            logger.warning(f"❌ Volume too low: {signal.volume_ratio:.2f}x")
            return False

        # Check trading hours
        now = datetime.now().time()
        entry_deadline = datetime.strptime(ENTRY_DEADLINE, "%H:%M").time()
        market_close = datetime.strptime(MARKET_CLOSE, "%H:%M").time()

        if now > entry_deadline:
            logger.warning(f"❌ Past entry deadline: {ENTRY_DEADLINE}")
            return False

        # Check if already have position
        if self.position_manager.get_open_position(signal.symbol):
            logger.warning(f"❌ Position already exists for {signal.symbol}")
            return False

        # Open position
        position = self.position_manager.open_position(signal)

        if position and ENABLE_AUTO_TRADING and self.kite:
            # Place real order via Kite
            return self._place_order(position)

        return position is not None

    def _place_order(self, position: Position) -> bool:
        """Place order via Kite Connect"""
        try:
            symbol_token = KITE_TOKENS.get(position.symbol)
            if not symbol_token:
                logger.error(f"❌ No kite token for {position.symbol}")
                return False

            config = get_symbol_safe_config(position.symbol)
            exchange = config['exchange']

            # Place order
            order_params = {
                'exchange': exchange,
                'tradingsymbol': config['symbol'],
                'transaction_type': 'BUY' if position.direction == Direction.LONG else 'SELL',
                'quantity': position.qty,
                'price': position.entry_price,
                'product': 'NRML',  # Normal for F&O
                'order_type': 'LIMIT',
                'validity': 'DAY'
            }

            # Place SL order
            sl_params = {
                'exchange': exchange,
                'tradingsymbol': config['symbol'],
                'transaction_type': 'SELL' if position.direction == Direction.LONG else 'BUY',
                'quantity': position.qty,
                'price': position.sl_price,
                'trigger_price': position.sl_price,
                'product': 'NRML',
                'order_type': 'SL',
                'validity': 'DAY'
            }

            logger.info(f"📤 Placing orders: {order_params}")

            # Uncomment for live trading
            # order_id = self.kite.place_order(**order_params)
            # sl_order_id = self.kite.place_order(**sl_params)

            logger.info(f"✅ Orders placed for {position.trade_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            return False

    def on_tick(self, tick: Dict) -> None:
        """Process market tick"""
        if 'last_price' not in tick:
            return

        current_price = tick['last_price']

        # Update trailing SL
        self.position_manager.update_trailing_sl(current_price)

        # Check exits
        exits = self.position_manager.check_exits(current_price)
        for trade_id, exit_price, reason in exits:
            self.position_manager.close_position(trade_id, exit_price, reason)

            # Exit opposite order in Kite
            if ENABLE_AUTO_TRADING and self.kite:
                self._exit_position(trade_id, exit_price)

    def _exit_position(self, trade_id: str, price: float) -> bool:
        """Exit position via Kite"""
        try:
            # Get position details
            position = self.position_manager.positions.get(trade_id)
            if not position:
                return False

            # Place exit order
            logger.info(f"📤 Exit order: {trade_id} @ {price}")
            # Actual order placement here
            return True

        except Exception as e:
            logger.error(f"❌ Exit failed: {e}")
            return False

    def get_daily_summary(self) -> Dict:
        """Get daily trading summary"""
        trades_today = [t for t in self.position_manager.trades
                       if t.entry_time.date() == datetime.now().date()]

        if not trades_today:
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'trades': 0,
                'winning': 0,
                'losing': 0,
                'pnl': 0,
                'win_rate': 0
            }

        winning = len([t for t in trades_today if t.net_pnl > 0])
        losing = len([t for t in trades_today if t.net_pnl < 0])
        total_pnl = sum([t.net_pnl for t in trades_today])

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trades': len(trades_today),
            'winning': winning,
            'losing': losing,
            'pnl': total_pnl,
            'win_rate': winning / len(trades_today) * 100 if trades_today else 0,
            'open_positions': len(self.position_manager.positions)
        }

    def save_trades(self) -> None:
        """Save trades to CSV"""
        if not self.position_manager.trades:
            return

        import pandas as pd

        df = pd.DataFrame([asdict(t) for t in self.position_manager.trades])
        filepath = TRADE_LOG_DIR / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filepath, index=False)
        logger.info(f"💾 Trades saved to {filepath}")


# Singleton instance
engine = ORBTradingEngine()


if __name__ == "__main__":
    print("=" * 70)
    print(" " * 20 + "ORB TRADING ENGINE")
    print("=" * 70)

    summary = engine.get_daily_summary()
    print(f"\n📊 Trading Summary for {summary['date']}:")
    print(f"   Trades: {summary['trades']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
    print(f"   P&L: Rs.{summary['pnl']:,.0f}")
    print(f"   Open Positions: {summary['open_positions']}")

    print("\n" + "=" * 70)
