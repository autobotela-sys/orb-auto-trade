"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    TRADINGVIEW WEBHOOK SERVER                                  ║
║                                                                               ║
║  Receives signals from TradingView alerts via webhook                         ║
║  Processes signals and executes trades via trading engine                     ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify

from config import (
    WEBHOOK_SECRET, WEBHOOK_PORT, ENABLE_AUTO_TRADING,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM_ALERTS
)
from trading_engine import engine, Signal, logger as engine_logger

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def send_telegram_alert(message: str) -> bool:
    """Send alert via Telegram"""
    if not ENABLE_TELEGRAM_ALERTS:
        return False

    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200

    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature for security"""
    if not WEBHOOK_SECRET:
        return True  # Skip verification if no secret set

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures
    return hmac.compare_digest(signature, expected_signature)


def parse_tradingview_alert(body: dict) -> Optional[Signal]:
    """
    Parse TradingView webhook alert body

    Expected format from TradingView alert message:
    {{ticker}}, {{time}}, {{close}}, {{orb_high}}, {{orb_low}}, {{volume_ratio}}, {{direction}}

    Example: "NIFTY, 09:35, 22450.00, 22470.00, 22430.00, 2.5, LONG"
    """
    try:
        # Get alert text
        alert_text = body.get('text', '')

        # Parse CSV format
        parts = [p.strip() for p in alert_text.split(',')]

        if len(parts) < 7:
            logger.error(f"Invalid alert format: {alert_text}")
            return None

        symbol_part = parts[0].strip()
        time_part = parts[1].strip()
        close_price = float(parts[2].strip())
        orb_high = float(parts[3].strip())
        orb_low = float(parts[4].strip())
        volume_ratio = float(parts[5].strip())
        direction = parts[6].strip().upper()

        # Map symbol
        symbol_map = {
            'NIFTY': 'NIFTY',
            'NIFTYFUT': 'NIFTY',
            'BANKNIFTY': 'BANKNIFTY',
            'BANKNIFTYFUT': 'BANKNIFTY',
            'FINNIFTY': 'FINNIFTY',
            'FINNIFTYFUT': 'FINNIFTY',
        }
        symbol = symbol_map.get(symbol_part.upper(), 'NIFTY')

        # Validate direction
        if direction not in ['LONG', 'SHORT', 'BUY', 'SELL']:
            logger.error(f"Invalid direction: {direction}")
            return None

        if direction == 'BUY':
            direction = 'LONG'
        elif direction == 'SELL':
            direction = 'SHORT'

        signal = Signal(
            direction=direction,
            entry_price=close_price,
            orb_high=orb_high,
            orb_low=orb_low,
            volume_ratio=volume_ratio,
            symbol=symbol
        )

        return signal

    except Exception as e:
        logger.error(f"Failed to parse alert: {e}")
        return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'auto_trading': ENABLE_AUTO_TRADING,
        'open_positions': len(engine.position_manager.positions)
    })


@app.route('/orb_signal', methods=['POST'])
def receive_signal():
    """Receive ORB signal from TradingView"""

    # Verify signature
    signature = request.headers.get('X-Webhook-Signature', '')
    if WEBHOOK_SECRET and not verify_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({'error': 'Invalid signature'}), 401

    # Parse signal
    try:
        data = request.get_json(force=True)
        logger.info(f"📥 Received webhook: {json.dumps(data, indent=2)[:200]}...")
    except Exception as e:
        logger.error(f"Failed to parse webhook data: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400

    signal = parse_tradingview_alert(data)
    if not signal:
        return jsonify({'error': 'Failed to parse signal'}), 400

    # Send Telegram alert
    telegram_msg = (
        f"🚨 <b>ORB Signal Received</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Symbol: {signal.symbol}\n"
        f"📈 Direction: {signal.direction}\n"
        f"💰 Entry: {signal.entry_price:.2f}\n"
        f"🔴 ORB High: {signal.orb_high:.2f}\n"
        f"🟢 ORB Low: {signal.orb_low:.2f}\n"
        f"📊 Volume: {signal.volume_ratio:.2f}x\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    send_telegram_alert(telegram_msg)

    # Process signal
    success = engine.process_signal(signal)

    if success:
        response_msg = (
            f"✅ <b>Order Placed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Trade executed successfully"
        )
        send_telegram_alert(response_msg)

        return jsonify({
            'status': 'success',
            'message': 'Order placed',
            'signal': {
                'symbol': signal.symbol,
                'direction': signal.direction,
                'entry': signal.entry_price
            }
        }), 200
    else:
        response_msg = (
            f"❌ <b>Order Rejected</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Check risk management rules"
        )
        send_telegram_alert(response_msg)

        return jsonify({
            'status': 'rejected',
            'message': 'Order rejected by risk management'
        }), 200


@app.route('/status', methods=['GET'])
def get_status():
    """Get current trading status"""
    summary = engine.get_daily_summary()

    # Get open positions
    positions = []
    for pos in engine.position_manager.positions.values():
        positions.append({
            'trade_id': pos.trade_id,
            'symbol': pos.symbol,
            'direction': pos.direction.name,
            'entry': pos.entry_price,
            'qty': pos.qty,
            'sl': pos.sl_price,
            'target': pos.target_price,
            'pnl': 'OPEN'
        })

    return jsonify({
        'summary': summary,
        'positions': positions,
        'config': {
            'auto_trading': ENABLE_AUTO_TRADING,
            'telegram_alerts': ENABLE_TELEGRAM_ALERTS
        }
    })


@app.route('/positions', methods=['GET'])
def get_positions():
    """Get all open positions"""
    positions = []

    for pos in engine.position_manager.positions.values():
        unrealized_pnl = 0
        # Calculate unrealized P&L if we had current price
        positions.append({
            'trade_id': pos.trade_id,
            'symbol': pos.symbol,
            'direction': pos.direction.name,
            'entry_price': pos.entry_price,
            'qty': pos.qty,
            'sl_price': pos.sl_price,
            'target_price': pos.target_price,
            'entry_time': pos.entry_time.isoformat(),
            'trail_sl_triggered': pos.trail_sl_triggered
        })

    return jsonify({'positions': positions})


@app.route('/trades', methods=['GET'])
def get_trades():
    """Get all completed trades"""
    trades = []

    for trade in engine.position_manager.trades:
        trades.append({
            'trade_id': trade.trade_id,
            'symbol': trade.symbol,
            'direction': trade.direction,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'qty': trade.qty,
            'pnl': trade.net_pnl,
            'points': trade.points,
            'entry_time': trade.entry_time.isoformat(),
            'exit_time': trade.exit_time.isoformat(),
            'exit_reason': trade.exit_reason
        })

    return jsonify({'trades': trades})


@app.route('/close_all', methods=['POST'])
def close_all_positions():
    """Manually close all positions"""
    # Get current price (would need real-time data)
    # For now, just return status
    return jsonify({
        'status': 'manual_close_required',
        'message': 'Use your broker app to close positions'
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


def run_server():
    """Run the webhook server"""
    print("=" * 70)
    print(" " * 15 + "TRADINGVIEW WEBHOOK SERVER")
    print("=" * 70)

    print(f"\n🚀 Server starting...")
    print(f"   Port: {WEBHOOK_PORT}")
    print(f"   Endpoint: http://localhost:{WEBHOOK_PORT}/orb_signal")
    print(f"   Health: http://localhost:{WEBHOOK_PORT}/health")

    print(f"\n⚙️  Configuration:")
    print(f"   Auto Trading: {'🟢 ENABLED' if ENABLE_AUTO_TRADING else '🔴 DISABLED'}")
    print(f"   Telegram Alerts: {'🟢 ENABLED' if ENABLE_TELEGRAM_ALERTS else '🔴 DISABLED'}")

    if WEBHOOK_SECRET:
        print(f"   Webhook Secret: ✅ Set")
    else:
        print(f"   ⚠️  Webhook Secret: Not Set (recommended)")

    print("\n" + "=" * 70)
    print("\n📝 TradingView Alert Configuration:")
    print("───" * 20)
    print("\n1. Webhook URL:")
    print(f"   http://YOUR_SERVER_IP:{WEBHOOK_PORT}/orb_signal")
    print("\n2. Alert Message Template:")
    print("   {{ticker}}, {{time}}, {{close}}, {{plot_orb_high}}, {{plot_orb_low}}, {{plot_volume_ratio}}, {{strategy.order.action}}")
    print("\n3. Or use custom Pine Script output:")
    print('   alert("NIFTY," + str.tostring(time) + "," + str.tostring(close) + ",")')

    print("\n" + "=" * 70)
    print("\n✅ Server Ready! Waiting for signals...\n")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=WEBHOOK_PORT,
        debug=False,
        use_reloader=False
    )


if __name__ == '__main__':
    run_server()
