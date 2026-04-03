"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   OPENING RANGE BREAKOUT (ORB) STRATEGY                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

STRATEGY:
1. Define Opening Range (first X minutes of trading)
2. Wait for price to break ORB high (long) or low (short)
3. Enter on break with volume confirmation
4. Target: 1.5x ORB range or fixed points
5. SL: Other side of ORB or trailing

VARIATIONS TO TEST:
- ORB Duration: 15 min, 30 min
- Volume confirmation: None, 1.5x, 2x
- Entry type: Immediate break, pullback after break
- Target: ORB range, 30 pts, 40 pts, 50 pts
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"C:\Users\elamuruganm\Documents\Projects\BT\NiftyData\nifty_futures_1min_2016_2023.csv"
OUTPUT_DIR = r"C:\Users\elamuruganm\Documents\Projects\BT\results"

LOT_SIZE = 50
BROKERAGE = 40
SLIPPAGE = 0.0005

# Test Parameters
ORB_DURATION_OPTIONS = [15, 30]  # minutes
VOLUME_CONFIRM_OPTIONS = [1.0, 1.5, 2.0]  # volume ratio
ENTRY_WAIT_OPTIONS = [0, 5, 10]  # minutes to wait after ORB before trading
TARGET_OPTIONS = ['ORB', 30, 40, 50]  # 'ORB' = 1.5x ORB range
SL_OPTIONS = ['ORB_OPP', 20, 25, 30]  # 'ORB_OPP' = other side of ORB

TRAIN_START = "2016-01-01"
TRAIN_END = "2020-12-31"
TEST_START = "2021-01-01"
TEST_END = "2023-12-31"

print("=" * 100)
print(" " * 25 + "OPENING RANGE BREAKOUT (ORB) STRATEGY BACKTEST")
print("=" * 100)
print("\nSTRATEGY:")
print("  1. Define Opening Range (first X minutes)")
print("  2. Wait for break of ORB high/low")
print("  3. Enter on break with volume confirmation")
print("  4. Target: ORB range or fixed points")
print("  5. SL: Other side of ORB or fixed points")

print("\n" + "=" * 100)

# ════════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════════════════════════

print("\n[1/4] Loading data...")
df = pd.read_csv(DATA_PATH)
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df.set_index('DateTime')
df = df.between_time('09:15', '15:30')
df = df[~df.index.duplicated(keep='first')]

# Add date and time columns
df['Date'] = df.index.date
df['Time'] = df.index.hour * 60 + df.index.minute  # Minutes from midnight

# Volume MA
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

print(f"    Loaded: {len(df):,} bars from {df.index[0].date()} to {df.index[-1].date()}")
print(f"    Trading days: {df['Date'].nunique()}")

# ════════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ════════════════════════════════════════════════════════════════════════════════

print("\n[2/4] Building backtest engine...")

def calculate_costs(entry, exit_price):
    turnover = (entry + exit_price) * LOT_SIZE
    cost_pts = ((BROKERAGE +
                exit_price * LOT_SIZE * 0.0001 +
                (turnover / 10000000) * 1.7 * 2 +
                (BROKERAGE + (turnover / 10000000) * 1.7 * 2) * 0.18 +
                entry * LOT_SIZE * 0.00002) / LOT_SIZE) + ((entry + exit_price) * 0.5 * SLIPPAGE)
    return cost_pts


def backtest_orb(data, orb_duration, vol_confirm, entry_wait, target_type, sl_type, start_date, end_date):
    """Backtest ORB strategy"""

    # Filter by date
    mask = (data.index >= start_date) & (data.index <= end_date)
    d = data[mask].copy()

    if len(d) == 0:
        return pd.DataFrame()

    trades = []

    # Group by date
    for date, day_data in d.groupby('Date'):
        # Define ORB period (9:15 to 9:15 + orb_duration)
        orb_start_time = 9 * 60 + 15  # 9:15 AM
        orb_end_time = orb_start_time + orb_duration

        orb_data = day_data[day_data['Time'] <= orb_end_time]

        if len(orb_data) < 5:  # Need enough data
            continue

        # ORB High and Low
        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_range = orb_high - orb_low

        if orb_range < 5:  # ORB too narrow
            continue

        # Get ORB breakout candle
        orb_breakout_time = orb_end_time

        # Wait period before trading
        trade_start_time = orb_breakout_time + entry_wait

        # Get data after wait period
        post_orb = day_data[day_data['Time'] >= trade_start_time]

        if len(post_orb) < 2:
            continue

        # Find breakouts
        long_triggered = False
        short_triggered = False
        long_entry = 0
        short_entry = 0
        long_time = None
        short_time = None
        long_vol_ok = False
        short_vol_ok = False

        for idx, row in post_orb.iterrows():
            vol_ok = row['Volume_Ratio'] >= vol_confirm if not pd.isna(row['Volume_Ratio']) else False

            # Long breakout
            if not long_triggered and row['High'] > orb_high:
                if vol_ok or vol_confirm == 1.0:
                    long_triggered = True
                    long_entry = orb_high + 0.5  # Entry above ORB high
                    long_time = idx
                    long_vol_ok = vol_ok

            # Short breakout
            if not short_triggered and row['Low'] < orb_low:
                if vol_ok or vol_confirm == 1.0:
                    short_triggered = True
                    short_entry = orb_low - 0.5  # Entry below ORB low
                    short_time = idx
                    short_vol_ok = vol_ok

        # Process trades
        for direction, entry_price, entry_time, vol_ok in [
            (1, long_entry, long_time, long_vol_ok),
            (-1, short_entry, short_time, short_vol_ok)
        ]:
            if entry_price == 0 or entry_time is None:
                continue

            # Calculate SL
            if sl_type == 'ORB_OPP':
                sl_price = orb_low if direction == 1 else orb_high
            else:
                sl_price = (entry_price - sl_type) if direction == 1 else (entry_price + sl_type)

            # Calculate target
            if target_type == 'ORB':
                target_price = (entry_price + orb_range * 1.5) if direction == 1 else (entry_price - orb_range * 1.5)
            else:
                target_price = (entry_price + target_type) if direction == 1 else (entry_price - target_type)

            # Find exit
            exit_price = None
            exit_reason = None

            # Get data after entry
            entry_idx = day_data.index.get_loc(entry_time)
            for j in range(entry_idx + 1, min(entry_idx + 100, len(day_data))):
                row = day_data.iloc[j]

                # Time exit
                if row['Time'] >= 15 * 60 + 15:  # 3:15 PM
                    exit_price = row['Close']
                    exit_reason = 'Time'
                    break

                # SL
                if direction == 1 and row['Low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                elif direction == -1 and row['High'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break

                # Target
                if direction == 1 and row['High'] >= target_price:
                    exit_price = target_price
                    exit_reason = 'Target'
                    break
                elif direction == -1 and row['Low'] <= target_price:
                    exit_price = target_price
                    exit_reason = 'Target'
                    break

            if exit_price is None:
                exit_price = day_data.iloc[min(entry_idx + 99, len(day_data) - 1)]['Close']
                exit_reason = 'Max Bars'

            # Calculate P&L
            costs = calculate_costs(entry_price, exit_price)
            gross_pnl = (exit_price - entry_price) if direction == 1 else (entry_price - exit_price)
            net_pnl = gross_pnl - costs

            trades.append({
                'entry_time': entry_time,
                'exit_time': entry_time,  # Will update
                'direction': 'LONG' if direction == 1 else 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_range': orb_range,
                'target_type': target_type,
                'sl_type': sl_type,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'reason': exit_reason
            })

    return pd.DataFrame(trades)


# ════════════════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ════════════════════════════════════════════════════════════════════════════════

print("\n[3/4] Running backtests...")
print(f"    Testing {len(ORB_DURATION_OPTIONS)} × {len(VOLUME_CONFIRM_OPTIONS)} × "
      f"{len(ENTRY_WAIT_OPTIONS)} × {len(TARGET_OPTIONS)} × {len(SL_OPTIONS)} = "
      f"{len(ORB_DURATION_OPTIONS) * len(VOLUME_CONFIRM_OPTIONS) * len(ENTRY_WAIT_OPTIONS) * len(TARGET_OPTIONS) * len(SL_OPTIONS)} combinations\n")

all_results = []
test_count = 0
total_tests = (len(ORB_DURATION_OPTIONS) * len(VOLUME_CONFIRM_OPTIONS) *
                len(ENTRY_WAIT_OPTIONS) * len(TARGET_OPTIONS) * len(SL_OPTIONS))

for orb_dur in ORB_DURATION_OPTIONS:
    for vol_conf in VOLUME_CONFIRM_OPTIONS:
        for wait in ENTRY_WAIT_OPTIONS:
            for tgt in TARGET_OPTIONS:
                for sl in SL_OPTIONS:
                    test_count += 1

                    if test_count % 20 == 0:
                        print(f"    Progress: {test_count}/{total_tests}...")

                    # Train
                    train_trades = backtest_orb(df, orb_dur, vol_conf, wait, tgt, sl, TRAIN_START, TRAIN_END)

                    # Test
                    test_trades = backtest_orb(df, orb_dur, vol_conf, wait, tgt, sl, TEST_START, TEST_END)

                    for period, trades in [('TRAIN', train_trades), ('TEST', test_trades)]:
                        if len(trades) == 0:
                            continue

                        total = len(trades)
                        wins = (trades['net_pnl'] > 0).sum()
                        wr = (wins / total * 100)
                        pnl = trades['net_pnl'].sum()

                        win_trades = trades[trades['net_pnl'] > 0]
                        lose_trades = trades[trades['net_pnl'] < 0]
                        pf = abs(win_trades['net_pnl'].sum() / lose_trades['net_pnl'].sum()) if lose_trades['net_pnl'].sum() < 0 else 0

                        cumul = trades['net_pnl'].cumsum()
                        max_dd = (cumul - cumul.cummax()).min()

                        target_hits = (trades['reason'] == 'Target').sum()
                        target_rate = (target_hits / total * 100)

                        all_results.append({
                            'orb_duration': orb_dur,
                            'vol_confirm': vol_conf,
                            'entry_wait': wait,
                            'target': tgt,
                            'sl': sl,
                            'period': period,
                            'trades': total,
                            'win_rate': wr,
                            'target_rate': target_rate,
                            'pnl': pnl,
                            'pnl_rs': pnl * LOT_SIZE,
                            'profit_factor': pf,
                            'max_dd': max_dd,
                            'avg_pnl': trades['net_pnl'].mean(),
                        })

# ════════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════

print("\n[4/4] Analyzing results...")

results_df = pd.DataFrame(all_results)
Path(OUTPUT_DIR).mkdir(exist_ok=True)
results_df.to_csv(f"{OUTPUT_DIR}/orb_breakout_results.csv", index=False)

# Find consistent performers
consistent = []
for orb_dur in ORB_DURATION_OPTIONS:
    for vol_conf in VOLUME_CONFIRM_OPTIONS:
        for wait in ENTRY_WAIT_OPTIONS:
            for tgt in TARGET_OPTIONS:
                for sl in SL_OPTIONS:
                    train_data = results_df[
                        (results_df['orb_duration'] == orb_dur) &
                        (results_df['vol_confirm'] == vol_conf) &
                        (results_df['entry_wait'] == wait) &
                        (results_df['target'] == tgt) &
                        (results_df['sl'] == sl) &
                        (results_df['period'] == 'TRAIN')
                    ]
                    test_data = results_df[
                        (results_df['orb_duration'] == orb_dur) &
                        (results_df['vol_confirm'] == vol_conf) &
                        (results_df['entry_wait'] == wait) &
                        (results_df['target'] == tgt) &
                        (results_df['sl'] == sl) &
                        (results_df['period'] == 'TEST')
                    ]

                    if len(train_data) > 0 and len(test_data) > 0:
                        train_pnl = train_data.iloc[0]['pnl']
                        test_pnl = test_data.iloc[0]['pnl']
                        train_trades = train_data.iloc[0]['trades']
                        test_trades = test_data.iloc[0]['trades']

                        if train_pnl > 0 and test_pnl > 0 and train_trades > 100 and test_trades > 50:
                            consistent.append({
                                'orb_duration': orb_dur,
                                'vol_confirm': vol_conf,
                                'entry_wait': wait,
                                'target': tgt,
                                'sl': sl,
                                'train_pnl': train_pnl,
                                'test_pnl': test_pnl,
                                'total_pnl': train_pnl + test_pnl,
                                'train_wr': train_data.iloc[0]['win_rate'],
                                'test_wr': test_data.iloc[0]['win_rate'],
                                'train_pf': train_data.iloc[0]['profit_factor'],
                                'test_pf': test_data.iloc[0]['profit_factor'],
                                'train_trades': int(train_trades),
                                'test_trades': int(test_trades),
                                'train_target': train_data.iloc[0]['target_rate'],
                                'test_target': test_data.iloc[0]['target_rate'],
                            })

consistent_df = pd.DataFrame(consistent)

if len(consistent_df) > 0:
    consistent_df = consistent_df.sort_values('total_pnl', ascending=False)
    consistent_df.to_csv(f"{OUTPUT_DIR}/orb_consistent.csv", index=False)

# ════════════════════════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 100)
print(" " * 30 + "ORB BREAKOUT STRATEGY RESULTS")
print("=" * 100)

if len(consistent_df) > 0:
    print(f"\n[1] CONSISTENTLY PROFITABLE: {len(consistent_df)} combinations found!")
    print("-" * 100)

    for i, (_, row) in enumerate(consistent_df.head(5).iterrows(), 1):
        tgt_str = f"{row['target']} pts" if isinstance(row['target'], (int, float)) else row['target']
        sl_str = f"{row['sl']} pts" if isinstance(row['sl'], (int, float)) else row['sl']

        print(f"\n#{i}. ORB: {row['orb_duration']} min | Vol: >{row['vol_confirm']}x | Wait: {row['entry_wait']} min")
        print(f"    Target: {tgt_str} | SL: {sl_str}")
        print(f"    ───────────────────────────────────────────────────────────────────────")
        print(f"    {'Period':<10} {'Trades':<10} {'Win %':<10} {'Target %':<12} {'Pnl (pts)':<15} {'Pnl (Rs)':<15} {'PF':<10}")
        print(f"    {'TRAIN':<10} {row['train_trades']:<10} {row['train_wr']:<10.1f} {row['train_target']:<12.1f} "
              f"{row['train_pnl']:<15.1f} Rs.{row['train_pnl']*LOT_SIZE:>10,.0f} {row['train_pf']:<10.2f}")
        print(f"    {'TEST':<10} {row['test_trades']:<10} {row['test_wr']:<10.1f} {row['test_target']:<12.1f} "
              f"{row['test_pnl']:<15.1f} Rs.{row['test_pnl']*LOT_SIZE:>10,.0f} {row['test_pf']:<10.2f}")
        print(f"    {'TOTAL':<10} {row['train_trades']+row['test_trades']:<10} "
              f"{(row['train_wr']+row['test_wr'])/2:<10.1f} "
              f"{(row['train_target']+row['test_target'])/2:<12.1f} "
              f"{row['total_pnl']:<15.1f} Rs.{row['total_pnl']*LOT_SIZE:>10,.0f}")

    print("\n" + "=" * 100)
    print("BEST CONFIGURATION:")
    print("=" * 100)
    best = consistent_df.iloc[0]
    tgt_str = f"{best['target']} pts" if isinstance(best['target'], (int, float)) else best['target']
    sl_str = f"{best['sl']} pts" if isinstance(best['sl'], (int, float)) else best['sl']

    print(f"ORB Duration: {best['orb_duration']} minutes")
    print(f"Volume Confirmation: Ratio > {best['vol_confirm']}x")
    print(f"Entry Wait: {best['entry_wait']} minutes after ORB")
    print(f"Target: {tgt_str}")
    print(f"Stop Loss: {sl_str}")
    print(f"\nTarget Hit Rate: Train {best['train_target']:.1f}% | Test {best['test_target']:.1f}%")
    print(f"\nExpected Monthly Return (1 lot): Rs. {best['total_pnl']*LOT_SIZE/8/12:,.0f}")
    print(f"Expected Monthly Return (5 lots): Rs. {best['total_pnl']*LOT_SIZE*5/8/12:,.0f}")

else:
    print("\n[1] NO CONSISTENTLY PROFITABLE COMBINATIONS")
    print("\n[2] BEST TEST PERFORMERS:")

    test_results = results_df[results_df['period'] == 'TEST'].copy()
    test_results = test_results[test_results['trades'] >= 50]
    test_results = test_results.sort_values('pnl', ascending=False)

    if len(test_results) > 0:
        for i, (_, row) in enumerate(test_results.head(10).iterrows(), 1):
            tgt_str = f"{row['target']}" if isinstance(row['target'], str) else f"{row['target']} pts"
            sl_str = f"{row['sl']}" if isinstance(row['sl'], str) else f"{row['sl']} pts"

            print(f"   #{i}. ORB: {row['orb_duration']}min | Vol: >{row['vol_confirm']}x | Wait: {row['entry_wait']}min")
            print(f"       Tgt: {tgt_str} | SL: {sl_str}")
            print(f"       P&L: Rs.{row['pnl_rs']:>10,.0f} | {row['trades']:>4} trades | "
                  f"{row['win_rate']:.1f}% WR | {row['target_rate']:.1f}% Target | PF: {row['profit_factor']:.2f}")

# Parameter analysis
print("\n[3] PARAMETER ANALYSIS:")
print("-" * 100)

for param in ['orb_duration', 'vol_confirm', 'entry_wait', 'target', 'sl']:
    print(f"\n{param}:")
    param_stats = results_df[results_df['period'] == 'TEST'].groupby(param).agg({
        'pnl': 'mean',
        'win_rate': 'mean',
        'target_rate': 'mean',
        'trades': 'sum'
    }).sort_values('pnl', ascending=False)

    for val, row in param_stats.iterrows():
        print(f"    {val}: P&L {row['pnl']:.0f} pts | WR {row['win_rate']:.1f}% | "
              f"Target {row['target_rate']:.1f}% | Trades {int(row['trades'])}")

print("\n" + "=" * 100)
print(f"Full results saved to: {OUTPUT_DIR}/orb_breakout_results.csv")
print("=" * 100)
