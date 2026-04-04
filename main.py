"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    QUANDBACK PRO - MAIN APPLICATION                            ║
║                   Generic Backtesting & Strategy Analysis System               ║
║                   Railway Deployment - Flask App with Database                 ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import pandas as pd
import numpy as np

# Configuration
from config import (
    SYMBOL_CONFIG, DEFAULT_SYMBOL, CAPITAL,
    ENABLE_AUTO_TRADING, ENABLE_TELEGRAM_ALERTS,
    LOG_DIR, TRADE_LOG_DIR
)

# Create directories
LOG_DIR.mkdir(exist_ok=True)
TRADE_LOG_DIR.mkdir(exist_ok=True)
(Path(__file__).parent / "data" / "backtest").mkdir(parents=True, exist_ok=True)
(Path(__file__).parent / "data" / "historical").mkdir(parents=True, exist_ok=True)

# Initialize Flask
app = Flask(__name__,
            template_folder='railway/templates',
            static_folder='railway/static')

# Database Configuration (Railway PostgreSQL)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///orb_trade.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'orb-secret-key-change-in-production')

# Initialize Database
db = SQLAlchemy(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Trade(db.Model):
    """Trade records"""
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(50), unique=True, nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime, nullable=False)
    exit_reason = db.Column(db.String(50))
    gross_pnl = db.Column(db.Float, default=0)
    costs = db.Column(db.Float, default=0)
    net_pnl = db.Column(db.Float, default=0)
    points = db.Column(db.Float, default=0)
    orb_high = db.Column(db.Float)
    orb_low = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'qty': self.qty,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'gross_pnl': self.gross_pnl,
            'costs': self.costs,
            'net_pnl': self.net_pnl,
            'points': self.points,
            'orb_high': self.orb_high,
            'orb_low': self.orb_low
        }


class BacktestResult(db.Model):
    """Backtest results"""
    __tablename__ = 'backtest_results'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Parameters
    orb_duration = db.Column(db.Integer)
    target = db.Column(db.Integer)
    sl = db.Column(db.Integer)
    volume_confirm = db.Column(db.Float)

    # Results
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    win_rate = db.Column(db.Float, default=0)
    total_pnl = db.Column(db.Float, default=0)
    total_points = db.Column(db.Float, default=0)
    avg_win = db.Column(db.Float, default=0)
    avg_loss = db.Column(db.Float, default=0)
    profit_factor = db.Column(db.Float, default=0)
    max_drawdown = db.Column(db.Float, default=0)
    max_drawdown_pct = db.Column(db.Float, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'orb_duration': self.orb_duration,
            'target': self.target,
            'sl': self.sl,
            'volume_confirm': self.volume_confirm,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_points': self.total_points,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class HistoricalData(db.Model):
    """Historical OHLCV data storage"""
    __tablename__ = 'historical_data'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=True)
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)
    oi = db.Column(db.BigInteger, nullable=True)  # Open Interest

    __table_args__ = (
        db.UniqueConstraint('symbol', 'date', 'time', name='unique_symbol_datetime'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.isoformat() if self.time else None,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'oi': self.oi
        }


class Signal(db.Model):
    """Incoming signals log"""
    __tablename__ = 'signals'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    orb_high = db.Column(db.Float)
    orb_low = db.Column(db.Float)
    volume_ratio = db.Column(db.Float)
    processed = db.Column(db.Boolean, default=False)
    order_placed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'orb_high': self.orb_high,
            'orb_low': self.orb_low,
            'volume_ratio': self.volume_ratio,
            'processed': self.processed,
            'order_placed': self.order_placed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES - WEB UI
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Dashboard home"""
    # Get stats
    total_trades = Trade.query.count()
    total_backtests = BacktestResult.query.count()

    # Recent trades
    recent_trades = Trade.query.order_by(Trade.entry_time.desc()).limit(10).all()

    # Recent backtests
    recent_backtests = BacktestResult.query.order_by(BacktestResult.created_at.desc()).limit(5).all()

    # Calculate summary
    if total_trades > 0:
        pnl_result = db.session.query(
            func.sum(Trade.net_pnl).label('total_pnl'),
            func.count(Trade.id).label('count'),
            func.sum(case_when(Trade.net_pnl > 0, 1)).label('wins')
        ).first()

        total_pnl = pnl_result.total_pnl or 0
        wins = pnl_result.wins or 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    else:
        total_pnl = 0
        win_rate = 0

    return render_template('dashboard.html',
                           total_trades=total_trades,
                           total_backtests=total_backtests,
                           total_pnl=total_pnl,
                           win_rate=win_rate,
                           recent_trades=recent_trades,
                           recent_backtests=recent_backtests,
                           enable_auto_trading=ENABLE_AUTO_TRADING)


@app.route('/trades')
def trades():
    """Trades page"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    trades = Trade.query.order_by(Trade.entry_time.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('trades.html', trades=trades)


@app.route('/backtests')
def backtests():
    """Backtests page"""
    backtests = BacktestResult.query.order_by(BacktestResult.created_at.desc()).all()
    return render_template('backtests.html', backtests=backtests)


@app.route('/backtest/new')
def backtest_new():
    """New backtest form"""
    error = request.args.get('error', '')
    return render_template('backtest_form.html', symbols=list(SYMBOL_CONFIG.keys()) + ['NIFTY_SPOT', 'NIFTY_FUT', 'BANKNIFTY_SPOT', 'BANKNIFTY_FUT'], error=error)


@app.route('/backtest/run', methods=['POST'])
def backtest_run():
    """Run backtest"""
    from backtest_engine import ORBBacktestEngine

    symbol = request.form.get('symbol', DEFAULT_SYMBOL)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    orb_duration = int(request.form.get('orb_duration', 15))
    target = int(request.form.get('target', 50))
    sl = int(request.form.get('sl', 30))
    volume_confirm = float(request.form.get('volume_confirm', 2.0))

    try:
        # Run backtest
        engine = ORBBacktestEngine(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            orb_duration=orb_duration,
            target=target,
            sl=sl,
            volume_confirm=volume_confirm,
            db_session=db.session  # Pass the Flask-SQLAlchemy session
        )

        results = engine.run()

        # Save to database
        backtest = BacktestResult(
            name=f"{symbol} Strategy Backtest",
            symbol=symbol,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            orb_duration=orb_duration,
            target=target,
            sl=sl,
            volume_confirm=volume_confirm,
            total_trades=results['total_trades'],
            winning_trades=results['winning_trades'],
            losing_trades=results['losing_trades'],
            win_rate=results['win_rate'],
            total_pnl=results['total_pnl'],
            total_points=results['total_points'],
            avg_win=results['avg_win'],
            avg_loss=results['avg_loss'],
            profit_factor=results['profit_factor'],
            max_drawdown=results['max_drawdown'],
            max_drawdown_pct=results['max_drawdown_pct']
        )

        db.session.add(backtest)
        db.session.commit()

        return redirect(url_for('backtest_view', id=backtest.id))

    except ValueError as e:
        # Handle expected errors (no data, invalid dates, etc.)
        logger.error(f"Backtest ValueError: {e}")
        return redirect(url_for('backtest_new', error=str(e)))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('backtest_new', error="Unexpected error occurred"))


@app.route('/backtest/<int:id>')
def backtest_view(id):
    """View backtest result"""
    backtest = BacktestResult.query.get_or_404(id)
    return render_template('backtest_view.html', backtest=backtest)


@app.route('/data')
def data_page():
    """Historical data page"""
    symbols = db.session.query(HistoricalData.symbol).distinct().all()
    symbols = [s[0] for s in symbols]

    return render_template('data.html', symbols=symbols)


@app.route('/signals')
def signals():
    """Signals log page"""
    signals = Signal.query.order_by(Signal.created_at.desc()).limit(100).all()
    return render_template('signals.html', signals=signals)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES - API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'auto_trading': ENABLE_AUTO_TRADING,
        'database': 'connected'
    }), 200


@app.route('/init_db')
def init_db_endpoint():
    """Initialize database tables endpoint"""
    try:
        db.create_all()
        return jsonify({'status': 'success', 'message': 'Database tables created'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/orb_signal', methods=['POST'])
def receive_signal():
    """Receive ORB signal from TradingView"""
    from trading_engine import engine, Signal

    # Parse signal
    data = request.get_json(force=True)
    logger.info(f"Webhook received: {data}")

    # Parse TradingView alert
    signal = parse_tradingview_alert(data)
    if not signal:
        return jsonify({'error': 'Failed to parse signal'}), 400

    # Log signal to database
    signal_record = Signal(
        symbol=signal.symbol,
        direction=signal.direction,
        entry_price=signal.entry_price,
        orb_high=signal.orb_high,
        orb_low=signal.orb_low,
        volume_ratio=signal.volume_ratio
    )
    db.session.add(signal_record)

    # Process signal
    success = engine.process_signal(signal)
    signal_record.processed = True
    signal_record.order_placed = success
    db.session.commit()

    if success:
        return jsonify({'status': 'success', 'message': 'Order placed'}), 200
    else:
        return jsonify({'status': 'rejected', 'message': 'Order rejected'}), 200


@app.route('/api/status')
def api_status():
    """Get current status"""
    from trading_engine import engine

    summary = engine.get_daily_summary()

    positions = []
    for pos in engine.position_manager.positions.values():
        positions.append({
            'trade_id': pos.trade_id,
            'symbol': pos.symbol,
            'direction': pos.direction.name,
            'entry': pos.entry_price,
            'qty': pos.qty,
            'sl': pos.sl_price,
            'target': pos.target_price
        })

    return jsonify({
        'summary': summary,
        'positions': positions,
        'config': {
            'auto_trading': ENABLE_AUTO_TRADING,
            'telegram_alerts': ENABLE_TELEGRAM_ALERTS
        }
    })


@app.route('/api/data/upload', methods=['POST'])
def upload_historical_data():
    """Upload historical data for backtesting"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    symbol = request.form.get('symbol', 'NIFTY_FUT')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Read CSV
    try:
        df = pd.read_csv(file)

        # Normalize column names to lowercase
        original_columns = df.columns.tolist()
        df.columns = df.columns.str.strip().str.lower()

        # Store datetime column before renaming
        datetime_col = None
        for col in df.columns:
            if col in ['datetime', 'timestamp']:
                datetime_col = col
                break

        # Column name mapping for common variations (but don't rename datetime yet)
        col_mapping = {
            'oi': 'oi',
            'openinterest': 'oi'
        }
        df = df.rename(columns=col_mapping)

        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close']
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            return jsonify({
                'error': f'Missing required columns: {missing}',
                'found_columns': list(df.columns),
                'hint': 'CSV must have: open, high, low, close (and optionally: date, time, volume)'
            }), 400

        # Handle datetime/date column
        if datetime_col:
            # Parse datetime column
            df['_datetime'] = pd.to_datetime(df[datetime_col], errors='coerce')
            df['date'] = df['_datetime'].dt.date
            # Convert time to string for SQLite compatibility
            df['time'] = df['_datetime'].dt.strftime('%H:%M:%S')
            df = df.drop(columns=['_datetime', datetime_col])
        elif 'date' not in df.columns:
            # Create dummy dates if no date column
            df['date'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
            df['time'] = None
        else:
            # date column exists but no datetime
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            df['time'] = None

        # Handle volume column - if not present, set to 0
        if 'volume' not in df.columns:
            df['volume'] = 0

        # Clean and convert data
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)

        # Drop rows with invalid OHLC data
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'date'])

        # Insert into database
        count = 0
        skipped = 0
        for _, row in df.iterrows():
            # Check if exists - match on symbol, date, time, AND OHLC values
            # This prevents false duplicates when time is None
            row_time = row['time'] if pd.notna(row['time']) else None

            existing = HistoricalData.query.filter_by(
                symbol=symbol,
                date=row['date'],
                time=row_time
            ).filter(
                HistoricalData.open == float(row['open']),
                HistoricalData.close == float(row['close'])
            ).first()

            if not existing:
                data = HistoricalData(
                    symbol=symbol,
                    date=row['date'],
                    time=row_time,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume'])
                )
                db.session.add(data)
                count += 1
            else:
                skipped += 1

        db.session.commit()

        message = f'Uploaded {count} new records for {symbol}'
        if skipped > 0:
            message += f' (skipped {skipped} exact duplicates)'

        return jsonify({
            'status': 'success',
            'message': message,
            'uploaded': count,
            'skipped': skipped
        }), 200

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/historical')
def api_historical_data():
    """Get historical data for backtesting"""
    symbol = request.args.get('symbol', 'NIFTY_FUT')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = HistoricalData.query.filter_by(symbol=symbol)

    if start_date:
        query = query.filter(HistoricalData.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(HistoricalData.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    data = query.order_by(HistoricalData.date, HistoricalData.time).all()

    return jsonify({
        'symbol': symbol,
        'count': len(data),
        'data': [d.to_dict() for d in data]
    })


@app.route('/api/data/clear/<symbol>', methods=['DELETE'])
def clear_historical_data(symbol):
    """Clear all historical data for a symbol"""
    try:
        deleted = HistoricalData.query.filter_by(symbol=symbol.upper()).delete()
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted} records for {symbol.upper()}'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Clear data error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
def api_trades():
    """Get all trades"""
    trades = Trade.query.order_by(Trade.entry_time.desc()).all()
    return jsonify({
        'trades': [t.to_dict() for t in trades]
    })


@app.route('/api/backtests')
def api_backtests():
    """Get all backtests"""
    backtests = BacktestResult.query.order_by(BacktestResult.created_at.desc()).all()
    return jsonify({
        'backtests': [b.to_dict() for b in backtests]
    })


def parse_tradingview_alert(data):
    """Parse TradingView webhook alert"""
    from trading_engine import Signal

    try:
        alert_text = data.get('text', '')
        parts = [p.strip() for p in alert_text.split(',')]

        if len(parts) < 7:
            return None

        symbol_part = parts[0].strip()
        close_price = float(parts[2].strip())
        orb_high = float(parts[3].strip())
        orb_low = float(parts[4].strip())
        volume_ratio = float(parts[5].strip())
        direction = parts[6].strip().upper()

        # Map symbol to new naming convention
        symbol_map = {
            'NIFTY': 'NIFTY_SPOT',
            'NIFTYFUT': 'NIFTY_FUT',
            'NIFTY_FUT': 'NIFTY_FUT',
            'NIFTY SPOT': 'NIFTY_SPOT',
            'BANKNIFTY': 'BANKNIFTY_SPOT',
            'BANKNIFTYFUT': 'BANKNIFTY_FUT',
            'BANKNIFTY_FUT': 'BANKNIFTY_FUT',
            'BANKNIFTY SPOT': 'BANKNIFTY_SPOT',
            'NIFTYFUTURES': 'NIFTY_FUT',
            'BANKNIFTYFUTURES': 'BANKNIFTY_FUT',
        }
        symbol = symbol_map.get(symbol_part.upper(), 'NIFTY_FUT')

        if direction == 'BUY':
            direction = 'LONG'
        elif direction == 'SELL':
            direction = 'SHORT'

        return Signal(
            direction=direction,
            entry_price=close_price,
            orb_high=orb_high,
            orb_low=orb_low,
            volume_ratio=volume_ratio,
            symbol=symbol
        )
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None


# SQLAlchemy case_when helper
from sqlalchemy.sql import case


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        logger.info("✅ Database initialized")


# Initialize database on import (for gunicorn/Railway)
try:
    init_db()
except Exception as e:
    logger.warning(f"Database init failed: {e}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 Starting QuantBack Pro on port {port}")
    logger.info(f"   Live Mode: {'ENABLED' if ENABLE_AUTO_TRADING else 'DISABLED'}")

    app.run(host='0.0.0.0', port=port, debug=False)
