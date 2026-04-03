"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   ORB BREAKOUT - ROBUST 10-YEAR BACKTEST                            ║
║                   Processes data year by year to avoid memory issues                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np

DATA_PATH = r"C:/Users/elamuruganm/Documents/Projects/BT/NiftyData/nifty_futures_1min_2016_2023.csv"
OUTPUT_DIR = r"C:/Users/elamuruganm/Documents/Projects/BT/results"

LOT_SIZE = 50
COST_PER_TRADE = 2.0

TRAIN_START = "2016-01-01"
TRAIN_END = "2020-12-31"
TEST_START = "2021-01-01"
TEST_END = "2023-02-28"

print("=" * 100)
print(" " * 25 + "ORB BREAKOUT - ROBUST 10-YEAR BACKTEST")
print("=" * 100)

print("\nLoading data...")
df = pd.read_csv(DATA_PATH)
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df.set_index('DateTime')
df = df.between_time('09:15', '15:30')
df = df[~df.index.duplicated(keep='first')]

df['Date'] = df.index.date
df['Year'] = df.index.year
df['Time'] = df.index.hour * 60 + df.index.minute
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

print(f"Loaded: {len(df):,} bars")
print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")

# ══════════════════════════════════════════════════════════════════════════════
# BACKTEST FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def backtest_orb(data, orb_dur, vol_conf, wait_min, target_pts, sl_pts):
    """Simple ORB backtest"""

    results = []

    for date, day_data in df.groupby('Date'):
        # ORB: 9:15 to 9:15+orb_dur
        orb_end_time = 9 * 60 + 15 + orb_dur
        orb_data = day_data[day_data['Time'] <= orb_end_time]

        if len(orb_data) < 5:
            continue

        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_range = orb_high - orb_low

        if orb_range < 5:
            continue

        # Trade period
        trade_start = orb_end_time + wait_min
        trade_data = day_data[day_data['Time'] >= trade_start]

        if len(trade_data) < 2:
            continue

        # Find first breakout
        long_breakout = trade_data[trade_data['High'] > orb_high]
        short_breakout = trade_data[trade_data['Low'] < orb_low]

        for idx in trade_data.index:
            vol_ok = trade_data.loc[idx, 'Volume_Ratio'] >= vol_conf

            # Long
            if len(long_breakout) > 0 and idx == long_breakout.index[0]:
                if vol_ok:
                    entry = orb_high + 0.5
                    sl = orb_low
                    tgt = entry + target_pts

                    entry_idx = day_data.index.get_loc(idx)

                    for j in range(entry_idx + 1, min(entry_idx + 50, len(day_data))):
                        r = day_data.iloc[j]

                        if r['Time'] >= 915:
                            exit_p = r['Close']
                            break
                        if r['Low'] <= sl:
                            exit_p = sl
                            break
                        if r['High'] >= tgt:
                            exit_p = tgt
                            break

                    exit_p = exit_p if exit_p is not None else day_data.iloc[min(entry_idx + 49, len(day_data) - 1)]['Close']
                    results.append({'pnl': exit_p - entry - COST_PER_TRADE})
                break

            # Short
            if len(short_breakout) > 0 and idx == short_breakout.index[0]:
                if vol_ok:
                    entry = orb_low - 0.5
                    sl = orb_high
                    tgt = entry - target_pts

                    entry_idx = day_data.index.get_loc(idx)

                    for j in range(entry_idx + 1, min(entry_idx + 50, len(day_data))):
                        r = day_data.iloc[j]

                        if r['Time'] >= 915:
                            exit_p = r['Close']
                            break
                        if r['High'] >= sl:
                            exit_p = sl
                            break
                        if r['Low'] <= tgt:
                            exit_p = tgt
                            break

                    exit_p = exit_p if exit_p is not None else day_data.iloc[min(entry_idx + 49, len(day_data) - 1)]['Close']
                    results.append({'pnl': entry - exit_p - COST_PER_TRADE})
                break

    return pd.DataFrame(results)


# Test configurations
print("\nRunning backtests...")

configs = [
    (15, 1.5, 0, 40, 25),
    (15, 1.5, 0, 50, 30),
    (15, 2.0, 0, 40, 25),
    (15, 2.0, 0, 50, 30),
    (15, 2.0, 0, 40, 30),
    (20, 1.5, 0, 40, 25),
    (20, 1.5, 0, 50, 30),
    (20, 2.0, 0, 40, 25),
    (20, 2.0, 0, 50, 30),
    (30, 1.5, 0, 40, 25),
    (30, 2.0, 0, 50, 30),
]

all_stats = []

for orb_dur, vol_conf, wait, tgt, sl in configs:
    # Train
    train_data = df[(df.index >= TRAIN_START) & (df.index <= TRAIN_END)]
    train_trades = backtest_orb(train_data, orb_dur, vol_conf, wait, tgt, sl)

    # Test
    test_data = df[(df.index >= TEST_START) & (df.index <= TEST_END)]
    test_trades = backtest_orb(test_data, orb_dur, vol_conf, wait, tgt, sl)

    for period, trades in [('TRAIN', train_trades), ('TEST', test_trades)]:
        if len(trades) > 0:
            total = len(trades)
            wins = (trades['pnl'] > 0).sum()
            wr = (wins / total * 100)
            pnl = trades['pnl'].sum()

            win_t = trades[trades['pnl'] > 0]['pnl'].sum()
            lose_t = trades[trades['pnl'] < 0]['pnl'].sum()
            pf = abs(win_t / lose_t) if lose_t < 0 else 0

            all_stats.append({
                'orb_dur': orb_dur,
                'vol': vol_conf,
                'wait': wait,
                'tgt': tgt,
                'sl': sl,
                'period': period,
                'trades': total,
                'wr': wr,
                'pnl': pnl,
                'pnl_rs': pnl * LOT_SIZE,
                'pf': pf
            })

        # Print progress
        if period == 'TEST':
            print(f"  ORB:{orb_dur} Vol:{vol_conf} Wait:{wait} Tgt:{tgt} SL:{sl} | "
                  f"{total:4} trades | {wr:5.1f}% WR | P&L: Rs.{pnl*LOT_SIZE:>10,.0f}")

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

test_stats = [s for s in all_stats if s['period'] == 'TEST']

if test_stats:
    print(f"\n{'ORB':<6} {'Vol':<6} {'Wait':<6} {'Tgt':<6} {'SL':<6} {'Trades':<8} {'WR%':<8} {'P&L (Rs)':<15}")
    print("-" * 100)

    for s in test_stats:
        status = "PROFITABLE" if s['pnl'] > 0 else "LOSS"
        print(f"{s['orb_dur']:<6} {s['vol']:<6} {s['wait']:<6} {s['tgt']:<6} {s['sl']:<6} "
              f"{s['trades']:<8} {s['wr']:<8.1f} Rs.{s['pnl_rs']:>12,.0f} [{status}]")

print("\n" + "=" * 100)
