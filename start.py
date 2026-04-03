"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    ORB AUTO-TRADE SYSTEM - QUICK START                         ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required = ['flask', 'requests', 'pandas', 'numpy']
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("❌ Missing packages:", ", ".join(missing))
        print("   Run: pip install -r requirements.txt")
        return False

    return True

def check_config():
    """Check configuration validity"""
    from config import validate_config, ENABLE_AUTO_TRADING, ENABLE_TELEGRAM_ALERTS

    print("\n⚙️  Configuration Check:")
    print("   Auto Trading:", "🟢 ENABLED" if ENABLE_AUTO_TRADING else "🔴 DISABLED")
    print("   Telegram Alerts:", "🟢 ENABLED" if ENABLE_TELEGRAM_ALERTS else "🔴 DISABLED")

    if validate_config():
        print("   ✅ Configuration Valid")
        return True
    else:
        print("   ⚠️  Configuration issues found")
        return False

def show_menu():
    """Show main menu"""
    print("\n" + "=" * 70)
    print(" " * 20 + "ORB AUTO-TRADE SYSTEM")
    print("=" * 70)

    print("\n📋 Main Menu:")
    print("   1. Start Webhook Server")
    print("   2. Test Configuration")
    print("   3. View Trading Summary")
    print("   4. Run Backtest")
    print("   5. Exit")

    print("\n" + "=" * 70)

def start_webhook_server():
    """Start the webhook server"""
    print("\n🚀 Starting Webhook Server...")
    print("   Press Ctrl+C to stop\n")

    try:
        from webhook_server import run_server
        run_server()
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Make sure port 8080 is available")

def test_configuration():
    """Test system configuration"""
    from config import (
        SYMBOL_CONFIG, DEFAULT_SYMBOL, CAPITAL,
        KITE_API_KEY, KITE_ACCESS_TOKEN,
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    )

    print("\n" + "=" * 70)
    print(" " * 25 + "SYSTEM TEST")
    print("=" * 70)

    print("\n📊 Symbol Configuration:")
    for symbol, config in SYMBOL_CONFIG.items():
        print(f"   {symbol}: Lot={config['lot_size']}, Target={config['target']}, SL={config['sl']}")

    print(f"\n💰 Capital: Rs {CAPITAL:,.0f}")

    print(f"\n🔌 API Status:")
    kite_ok = bool(KITE_API_KEY and KITE_ACCESS_TOKEN)
    print(f"   Kite Connect: {'✅ Connected' if kite_ok else '❌ Not configured'}")

    print(f"\n📱 Telegram Status:")
    telegram_ok = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    print(f"   Alerts: {'✅ Ready' if telegram_ok else '❌ Not configured'}")

    print("\n" + "=" * 70)

    if kite_ok or telegram_ok:
        print("✅ System ready for testing")
    else:
        print("⚠️  Configure API credentials for live trading")

def view_trading_summary():
    """View trading summary"""
    from trading_engine import engine
    summary = engine.get_daily_summary()

    print("\n" + "=" * 70)
    print(" " * 25 + "TRADING SUMMARY")
    print("=" * 70)

    print(f"\n📅 Date: {summary['date']}")
    print(f"\n   Trades: {summary['trades']}")
    print(f"   Winning: {summary['winning']}")
    print(f"   Losing: {summary['losing']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
    print(f"   P&L: Rs.{summary['pnl']:,.0f}")
    print(f"   Open Positions: {summary['open_positions']}")

    # Show recent trades
    if engine.position_manager.trades:
        print(f"\n📜 Recent Trades:")
        for trade in engine.position_manager.trades[-5:]:
            print(f"   {trade.trade_id}: {trade.direction} {trade.entry_price:.0f} → {trade.exit_price:.0f} | Rs.{trade.net_pnl:,.0f}")

    print("\n" + "=" * 70)

def run_backtest():
    """Run ORB backtest"""
    print("\n📊 Running Backtest...")
    print("   Choose backtest file:")

    backtest_files = [
        "orb_10year_backtest.py",
        "orb_optimized_backtest.py",
        "orb_robust_backtest.py"
    ]

    for i, f in enumerate(backtest_files, 1):
        exists = (Path(__file__).parent / f).exists()
        status = "✅" if exists else "❌"
        print(f"   {i}. {f} {status}")

    print("\n   Run directly: python orb_10year_backtest.py")

def main():
    """Main entry point"""
    if not check_requirements():
        return

    while True:
        show_menu()
        choice = input("\n👉 Enter choice (1-5): ").strip()

        if choice == "1":
            start_webhook_server()
        elif choice == "2":
            test_configuration()
        elif choice == "3":
            view_trading_summary()
        elif choice == "4":
            run_backtest()
        elif choice == "5":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
