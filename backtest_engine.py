"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                        ORB BACKTEST ENGINE                                      ║
║                                                                               ║
║  Database-integrated backtesting for Railway deployment                       ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from config import SYMBOL_CONFIG, BROKERAGE_PER_ORDER, STT_BUY_RATE, STT_SELL_RATE, \
    TRANSACTION_CHARGE_PER_CRORE, GST_RATE, STAMP_DUTY_RATE

logger = logging.getLogger(__name__)


class ORBBacktestEngine:
    """ORB Strategy backtest engine with database integration"""

    # Default configs for backtesting when not in SYMBOL_CONFIG
    DEFAULT_CONFIGS = {
        'NIFTY_SPOT': {'lot_size': 50, 'tick_size': 0.05},
        'NIFTY_FUT': {'lot_size': 50, 'tick_size': 0.05},
        'BANKNIFTY_SPOT': {'lot_size': 15, 'tick_size': 0.05},
        'BANKNIFTY_FUT': {'lot_size': 15, 'tick_size': 0.05},
    }

    def __init__(
        self,
        symbol: str = "NIFTY_FUT",
        start_date: str = "2020-01-01",
        end_date: str = "2024-12-31",
        orb_duration: int = 15,
        target: int = 50,
        sl: int = 30,
        volume_confirm: float = 2.0,
        db_session=None  # Pass Flask-SQLAlchemy session
    ):
        self.symbol = symbol.upper()
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        self.orb_duration = orb_duration
        self.target = target
        self.sl = sl
        self.volume_confirm = volume_confirm
        self.db = db_session  # Store session for queries

        # Get config - try SYMBOL_CONFIG first, then DEFAULT_CONFIGS, then use fallback
        if self.symbol in SYMBOL_CONFIG:
            self.config = SYMBOL_CONFIG[self.symbol]
        elif self.symbol in self.DEFAULT_CONFIGS:
            self.config = self.DEFAULT_CONFIGS[self.symbol]
        else:
            # Fallback to NIFTY_FUT defaults
            self.config = self.DEFAULT_CONFIGS['NIFTY_FUT']

        self.lot_size = self.config.get('lot_size', 50)

        # Results storage
        self.trades = []
        self.equity_curve = []

    def load_data(self) -> pd.DataFrame:
        """Load historical data from database"""
        # Import here to avoid circular import
        from app import HistoricalData

        logger.info(f"Loading data for {self.symbol} from {self.start_date} to {self.end_date}")

        query = self.db.query(HistoricalData).filter_by(symbol=self.symbol)\
            .filter(HistoricalData.date >= self.start_date)\
            .filter(HistoricalData.date <= self.end_date)\
            .order_by(HistoricalData.date, HistoricalData.time)

        data = query.all()

        if not data:
            raise ValueError(f"No data found for {self.symbol} in specified date range")

        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': d.date,
            'time': d.time,
            'datetime': datetime.combine(d.date, d.time) if d.time else datetime.combine(d.date, time(0, 0)),
            'open': d.open,
            'high': d.high,
            'low': d.low,
            'close': d.close,
            'volume': d.volume
        } for d in data])

        logger.info(f"Loaded {len(df)} records")
        return df

    def calculate_orb_levels(self, day_data: pd.DataFrame) -> tuple:
        """Calculate ORB high and low for a day"""
        # Filter for ORB period (9:15 to 9:15 + orb_duration)
        orb_start = time(9, 15)
        orb_end_minutes = 9 * 60 + 15 + self.orb_duration
        orb_end_hour = orb_end_minutes // 60
        orb_end_min = orb_end_minutes % 60
        orb_end = time(orb_end_hour, orb_end_min)

        # Filter for ORB period
        orb_mask = (day_data['time'] >= orb_start) & (day_data['time'] < orb_end)
        orb_data = day_data[orb_mask]

        if orb_data.empty:
            return None, None

        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()

        # Calculate volume MA for confirmation
        vol_ma = day_data['volume'].rolling(window=20).mean().iloc[-1] if len(day_data) >= 20 else day_data['volume'].mean()

        return orb_high, orb_low, vol_ma

    def calculate_costs(self, entry: float, exit_price: float, qty: int) -> float:
        """Calculate trading costs"""
        turnover = (entry + exit_price) * qty
        brokerage = BROKERAGE_PER_ORDER * 2
        stt = exit_price * qty * STT_SELL_RATE
        transaction = (turnover / 10000000) * TRANSACTION_CHARGE_PER_CRORE * 2
        gst = (brokerage + transaction) * GST_RATE
        stamp = entry * qty * STAMP_DUTY_RATE

        total_cost_rs = brokerage + stt + transaction + gst + stamp
        return total_cost_rs / qty  # Cost per share/point

    def run(self) -> Dict:
        """Run the backtest"""
        logger.info(f"Starting backtest: {self.symbol} ORB Strategy")

        # Load data
        df = self.load_data()

        # Group by date
        df['date_only'] = df['datetime'].dt.date
        grouped = df.groupby('date_only')

        trades = []
        equity = self.config.get('initial_capital', 100000)
        equity_curve = [equity]
        peak_equity = equity
        max_drawdown = 0
        max_drawdown_pct = 0

        for date, day_data in grouped:
            # Skip if insufficient data
            if len(day_data) < 30:
                continue

            # Calculate ORB levels
            result = self.calculate_orb_levels(day_data)
            if result[0] is None:
                continue

            orb_high, orb_low, vol_ma = result

            # Trading after ORB period
            orb_start_idx = self.orb_duration  # Approximate
            after_orb = day_data.iloc[orb_start_idx:]

            # Track trade for the day
            day_trade = None

            for idx, row in after_orb.iterrows():
                if day_trade is not None:
                    # Check exits
                    if day_trade['direction'] == 'LONG':
                        pnl_points = row['close'] - day_trade['entry']

                        # SL hit
                        if row['low'] <= day_trade['sl']:
                            day_trade['exit'] = day_trade['sl']
                            day_trade['reason'] = 'SL'
                            day_trade['exit_time'] = row['datetime']
                            break

                        # Target hit
                        if row['high'] >= day_trade['target']:
                            day_trade['exit'] = day_trade['target']
                            day_trade['reason'] = 'Target'
                            day_trade['exit_time'] = row['datetime']
                            break

                    else:  # SHORT
                        pnl_points = day_trade['entry'] - row['close']

                        # SL hit
                        if row['high'] >= day_trade['sl']:
                            day_trade['exit'] = day_trade['sl']
                            day_trade['reason'] = 'SL'
                            day_trade['exit_time'] = row['datetime']
                            break

                        # Target hit
                        if row['low'] <= day_trade['target']:
                            day_trade['exit'] = day_trade['target']
                            day_trade['reason'] = 'Target'
                            day_trade['exit_time'] = row['datetime']
                            break

                # Entry logic (only if no trade yet)
                if day_trade is None:
                    vol_ratio = row['volume'] / vol_ma if vol_ma > 0 else 1

                    # Long entry
                    if row['close'] > orb_high and vol_ratio >= self.volume_confirm:
                        day_trade = {
                            'date': date,
                            'direction': 'LONG',
                            'entry': row['close'],
                            'orb_high': orb_high,
                            'orb_low': orb_low,
                            'sl': orb_low,
                            'target': orb_high + self.target,
                            'volume_ratio': vol_ratio,
                            'entry_time': row['datetime']
                        }

                    # Short entry
                    elif row['close'] < orb_low and vol_ratio >= self.volume_confirm:
                        day_trade = {
                            'date': date,
                            'direction': 'SHORT',
                            'entry': row['close'],
                            'orb_high': orb_high,
                            'orb_low': orb_low,
                            'sl': orb_high,
                            'target': orb_low - self.target,
                            'volume_ratio': vol_ratio,
                            'entry_time': row['datetime']
                        }

            # Close open trade at 3:15 PM
            if day_trade and 'exit' not in day_trade:
                last_row = after_orb.iloc[-1]
                day_trade['exit'] = last_row['close']
                day_trade['reason'] = 'Square Off'
                day_trade['exit_time'] = last_row['datetime']

            # Calculate P&L if trade completed
            if day_trade and 'exit' in day_trade:
                if day_trade['direction'] == 'LONG':
                    gross_pnl = day_trade['exit'] - day_trade['entry']
                else:
                    gross_pnl = day_trade['entry'] - day_trade['exit']

                costs = self.calculate_costs(day_trade['entry'], day_trade['exit'], self.lot_size)
                net_pnl_points = gross_pnl - costs
                net_pnl_rs = net_pnl_points * self.lot_size

                day_trade['gross_pnl'] = gross_pnl
                day_trade['costs'] = costs
                day_trade['net_pnl'] = net_pnl_points
                day_trade['net_pnl_rs'] = net_pnl_rs

                trades.append(day_trade)

                # Update equity
                equity += net_pnl_rs
                equity_curve.append(equity)

                # Track drawdown
                if equity > peak_equity:
                    peak_equity = equity
                drawdown = peak_equity - equity
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

        # Calculate results
        results = self._calculate_results(trades, equity_curve, max_drawdown, max_drawdown_pct)
        results['equity_curve'] = equity_curve

        logger.info(f"Backtest complete: {results['total_trades']} trades, Win Rate: {results['win_rate']:.1f}%")

        return results

    def _calculate_results(self, trades: List[Dict], equity_curve: List[float],
                          max_drawdown: float, max_drawdown_pct: float) -> Dict:
        """Calculate backtest results"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_points': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct
            }

        total_trades = len(trades)
        winning_trades = [t for t in trades if t['net_pnl'] > 0]
        losing_trades = [t for t in trades if t['net_pnl'] < 0]

        total_pnl = sum(t['net_pnl_rs'] for t in trades)
        total_points = sum(t['net_pnl'] for t in trades)

        avg_win = np.mean([t['net_pnl_rs'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['net_pnl_rs'] for t in losing_trades]) if losing_trades else 0

        gross_profit = sum(t['net_pnl_rs'] for t in winning_trades)
        gross_loss = abs(sum(t['net_pnl_rs'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'total_points': total_points,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'trades': trades
        }


def run_quick_backtest(symbol: str = "NIFTY_FUT", days: int = 30) -> Dict:
    """Quick backtest for last N days"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    engine = ORBBacktestEngine(
        symbol=symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    try:
        return engine.run()
    except ValueError as e:
        logger.error(f"Backtest failed: {e}")
        return {'error': str(e)}


if __name__ == '__main__':
    # Quick test
    results = run_quick_backtest('NIFTY_FUT', 30)
    print(results)
