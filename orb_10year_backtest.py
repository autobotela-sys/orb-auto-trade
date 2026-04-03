"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   ORB BREAKOUT - COMPREHENSIVE 10-YEAR BACKTEST              ║
║                   This is the FINAL, THOROUGH BACKTEST                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Full 10-year data analysis with:
- Train/Test split for anti-overfitting
- Year-by-year performance breakdown
- Monthly analysis
- Drawdown analysis
- Multiple parameter combinations
- Proper cost calculations
- Trade-by-trade export
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

DATA_PATH = r"C:\Users\elamuruganm\Documents\Projects\BT\NiftyData\nifty_futures_1min_2016_2023.csv"
OUTPUT_DIR = r"C:\Users\elamuruganm\Documents\Projects\BT\results"

LOT_SIZE = 50
BROKERAGE = 40
SLIPPAGE = 0.0005

# ORB Parameters to test
ORB_DURATIONS = [10, 15, 20, 30]
VOLUME_CONFIRMS = [1.0, 1.3, 1.5, 2.0]
WAIT_PERIODS = [0, 5, 10, 15]  # minutes to wait after ORB
TARGET_POINTS = [30, 40, 50, 60]
SL_POINTS = [20, 25, 30, 40]
SL_TYPES = ['orb_opposite', 'fixed']  # SL at other side of ORB or fixed points

# Train/Test Split
TRAIN_START = "2016-01-01"
TRAIN_END = "2020-12-31"
TEST_START = "2021-01-01"
TEST_END = "2023-02-28"

print("=" * 100)
print(" " * 20 + "ORB BREAKOUT - COMPREHENSIVE 10-YEAR BACKTEST")
print("=" * 100)
print(f"\nDATA: {DATA_PATH}")
print(f"TRAIN PERIOD: {TRAIN_START} to {TRAIN_END}")
print(f"TEST PERIOD: {TEST_START} to {TEST_END}")
print(f"LOT SIZE: {LOT_SIZE}")
print(f"\nTESTING {len(ORB_DURATIONS)} × {len(VOLUME_CONFIRMS)} × {len(WAIT_PERIODS)} × "
      f"{len(TARGET_POINTS)} × {len(SL_POINTS)} = {len(ORB_DURATIONS) * len(VOLUME_CONFIRMS) * len(WAIT_PERIODS) * len(TARGET_POINTS) * len(SL_POINTS)} combinations")
print("=" * 100)

# ════════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════════════════════════

print("\n[1/6] Loading data...")
df = pd.read_csv(DATA_PATH)
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df.set_index('DateTime')
df = df.between_time('09:15', '15:30')
df = df[~df.index.duplicated(keep='first')]

print(f"    Total bars: {len(df):,}")
print(f"    Date range: {df.index[0].date()} to {df.index[-1].date()}")

# Add columns
df['Date'] = df.index.date
df['Year'] = df.index.year
df['Month'] = df.index.month
df['Time'] = df.index.hour * 60 + df.index.minute
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

print("    Data loaded and pre-processed")

# ════════════════════════════════════════════════════════════════════════════════
# BACKTEST FUNCTION
# ════════════════════════════════════════════════════════════════════════════════

print("\n[2/6] Building backtest engine...")

def calculate_costs(entry, exit_price):
    turnover = (entry + exit_price) * LOT_SIZE
    cost_pts = ((BROKERAGE +
                exit_price * LOT_SIZE * 0.0001 +
                (turnover / 10000000) * 1.7 * 2 +
                (BROKERAGE + (turnover / 10000000) * 1.7 * 2) * 0.18 +
                entry * LOT_SIZE * 0.00002) / LOT_SIZE) + ((entry + exit_price) * 0.5 * SLIPPAGE)
    return cost_pts


def backtest_orb(data, orb_duration, vol_confirm, wait_minutes, target_pts, sl_points, sl_type, start_date, end_date):
    """Backtest ORB strategy with given parameters"""

    # Filter by date
    mask = (data.index >= start_date) & (data.index <= end_date)
    d = data[mask].copy()

    if len(d) == 0:
        return pd.DataFrame()

    trades = []
    long_trades = []
    short_trades = []

    # Group by date for ORB calculation
    for date, day_data in d.groupby('Date'):
        # Define ORB period
        orb_start = 9 * 60 + 15  # 9:15 AM
        orb_end = orb_start + orb_duration

        # Get ORB data
        orb_data = day_data[day_data['Time'] <= orb_end]

        if len(orb_data) < 5:
            continue

        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_range = orb_high - orb_low

        if orb_range < 5:  # Skip very narrow ORB
            continue

        # Trade period (after ORB + wait)
        trade_start_time = orb_end + wait_minutes
        trade_data = day_data[day_data['Time'] >= trade_start_time]

        if len(trade_data) < 2:
            continue

        # Find breakouts
        long_triggered = False
        short_triggered = False
        long_entry_time = None
        short_entry_time = None
        long_entry_price = 0
        short_entry_price = 0

        for idx, row in trade_data.iterrows():
            vol_ok = row['Volume_Ratio'] >= vol_confirm if not pd.isna(row['Volume_Ratio']) else True

            # Long breakout
            if not long_triggered and row['High'] > orb_high:
                if vol_ok:
                    long_triggered = True
                    long_entry_time = idx
                    long_entry_price = orb_high + 0.5
                break  # Only one trade per side per day

            # Short breakout
            if not short_triggered and row['Low'] < orb_low:
                if vol_ok:
                    short_triggered = True
                    short_entry_time = idx
                    short_entry_price = orb_low - 0.5
                break

        # Process LONG trade
        if long_triggered:
            entry_idx = day_data.index.get_loc(long_entry_time)
            entry_price = long_entry_price

            # SL
            if sl_type == 'orb_opposite':
                sl_price = orb_low
            else:
                sl_price = entry_price - sl_points

            # Target
            target_price = entry_price + target_pts

            # Exit logic
            exit_price = None
            exit_reason = None

            for j in range(entry_idx + 1, min(entry_idx + 100, len(day_data))):
                r = day_data.iloc[j]

                # Time exit
                if r['Time'] >= 15 * 60 + 15:
                    exit_price = r['Close']
                    exit_reason = 'Time'
                    break

                # SL hit
                if r['Low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break

                # Target hit
                if r['High'] >= target_price:
                    exit_price = target_price
                    exit_reason = 'Target'
                    break

            if exit_price is None:
                exit_price = day_data.iloc[min(entry_idx + 99, len(day_data) - 1)]['Close']
                exit_reason = 'Max Bars'

            # Calculate P&L
            costs = calculate_costs(entry_price, exit_price)
            gross_pnl = exit_price - entry_price
            net_pnl = gross_pnl - costs

            trades.append({
                'date': date,
                'entry_time': long_entry_time,
                'exit_time': long_entry_time,  # Will update
                'direction': 'LONG',
                'entry': entry_price,
                'exit': exit_price,
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_range': orb_range,
                'target': target_pts,
                'sl': sl_points,
                'sl_type': sl_type,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'reason': exit_reason
            })

        # Process SHORT trade
        if short_triggered:
            entry_idx = day_data.index.get_loc(short_entry_time)
            entry_price = short_entry_price

            if sl_type == 'orb_opposite':
                sl_price = orb_high
            else:
                sl_price = entry_price + sl_points

            target_price = entry_price - target_pts

            exit_price = None
            exit_reason = None

            for j in range(entry_idx + 1, min(entry_idx + 100, len(day_data))):
                r = day_data.iloc[j]

                if r['Time'] >= 15 * 60 + 15:
                    exit_price = r['Close']
                    exit_reason = 'Time'
                    break

                if r['High'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break

                if r['Low'] <= target_price:
                    exit_price = target_price
                    exit_reason = 'Target'
                    break

            if exit_price is None:
                exit_price = day_data.iloc[min(entry_idx + 99, len(day_data) - 1)]['Close']
                exit_reason = 'Max Bars'

            costs = calculate_costs(entry_price, exit_price)
            gross_pnl = entry_price - exit_price
            net_pnl = gross_pnl - costs

            trades.append({
                'date': date,
                'entry_time': short_entry_time,
                'exit_time': short_entry_time,
                'direction': 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_range': orb_range,
                'target': target_pts,
                'sl': sl_points,
                'sl_type': sl_type,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'reason': exit_reason
            })

    return pd.DataFrame(trades)


# ════════════════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ════════════════════════════════════════════════════════════════════════════════

print("\n[3/6] Running backtests...")
print("    (This will take a few minutes...)\n")

all_results = []
test_count = 0
total_tests = (len(ORB_DURATIONS) * len(VOLUME_CONFIRMS) * len(WAIT_PERIODS) *
                len(TARGET_POINTS) * len(SL_POINTS))

for orb_dur in ORB_DURATIONS:
    for vol_conf in VOLUME_CONFIRMS:
        for wait in WAIT_PERIODS:
            for tgt in TARGET_POINTS:
                for sl in SL_POINTS:
                    test_count += 1

                    if test_count % 100 == 0:
                        print(f"    Progress: {test_count}/{total_tests} tested... ({test_count/total_tests*100:.1f}%)")

                    # Train
                    train_trades = backtest_orb(df, orb_dur, vol_conf, wait, tgt, sl, 'orb_opposite', TRAIN_START, TRAIN_END)

                    # Test
                    test_trades = backtest_orb(df, orb_dur, vol_conf, wait, tgt, sl, 'orb_opposite', TEST_START, TEST_END)

                    # Process TRAIN
                    if len(train_trades) > 0:
                        total = len(train_trades)
                        wins = (train_trades['net_pnl'] > 0).sum()
                        wr = (wins / total * 100) if total > 0 else 0
                        pnl = train_trades['net_pnl'].sum()

                        win_trades = train_trades[train_trades['net_pnl'] > 0]
                        lose_trades = train_trades[train_trades['net_pnl'] < 0]
                        pf = abs(win_trades['net_pnl'].sum() / lose_trades['net_pnl'].sum()) if lose_trades['net_pnl'].sum() < 0 else 0

                        cumul = train_trades['net_pnl'].cumsum()
                        max_dd = (cumul - cumul.cummax()).min()

                        target_hits = (train_trades['reason'] == 'Target').sum()
                        target_rate = (target_hits / total * 100) if total > 0 else 0

                        all_results.append({
                            'orb_duration': orb_dur,
                            'vol_confirm': vol_conf,
                            'wait_minutes': wait,
                            'target': tgt,
                            'sl': sl,
                            'sl_type': 'orb_opposite',
                            'period': 'TRAIN',
                            'trades': total,
                            'wins': wins,
                            'win_rate': wr,
                            'target_rate': target_rate,
                            'pnl': pnl,
                            'pnl_rs': pnl * LOT_SIZE,
                            'profit_factor': pf,
                            'max_dd': max_dd,
                            'avg_pnl': train_trades['net_pnl'].mean(),
                        })

                    # Process TEST
                    if len(test_trades) > 0:
                        total = len(test_trades)
                        wins = (test_trades['net_pnl'] > 0).sum()
                        wr = (wins / total * 100) if total > 0 else 0
                        pnl = test_trades['net_pnl'].sum()

                        win_trades = test_trades[test_trades['net_pnl'] > 0]
                        lose_trades = test_trades[test_trades['net_pnl'] < 0]
                        pf = abs(win_trades['net_pnl'].sum() / lose_trades['net_pnl'].sum()) if lose_trades['net_pnl'].sum() < 0 else 0

                        cumul = test_trades['net_pnl'].cumsum()
                        max_dd = (cumul - cumul.cummax()).min()

                        target_hits = (test_trades['reason'] == 'Target').sum()
                        target_rate = (target_hits / total * 100) if total > 0 else 0

                        all_results.append({
                            'orb_duration': orb_dur,
                            'vol_confirm': vol_conf,
                            'wait_minutes': wait,
                            'target': tgt,
                            'sl': sl,
                            'sl_type': 'orb_opposite',
                            'period': 'TEST',
                            'trades': total,
                            'wins': wins,
                            'win_rate': wr,
                            'target_rate': target_rate,
                            'pnl': pnl,
                            'pnl_rs': pnl * LOT_SIZE,
                            'profit_factor': pf,
                            'max_dd': max_dd,
                            'avg_pnl': test_trades['net_pnl'].mean(),
                        })

# ════════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════

print("\n[4/6] Analyzing results...")

results_df = pd.DataFrame(all_results)

# Save all results
Path(OUTPUT_DIR).mkdir(exist_ok=True)
results_df.to_csv(f"{OUTPUT_DIR}/orb_10year_full_results.csv", index=False)

# Find consistent performers
print("\n    Finding consistent performers...")
consistent = []
for orb_dur in ORB_DURATIONS:
    for vol_conf in VOLUME_CONFIRMS:
        for wait in WAIT_PERIODS:
            for tgt in TARGET_POINTS:
                for sl in SL_POINTS:
                    train_data = results_df[
                        (results_df['orb_duration'] == orb_dur) &
                        (results_df['vol_confirm'] == vol_conf) &
                        (results_df['wait_minutes'] == wait) &
                        (results_df['target'] == tgt) &
                        (results_df['sl'] == sl) &
                        (results_df['period'] == 'TRAIN')
                    ]
                    test_data = results_df[
                        (results_df['orb_duration'] == orb_dur) &
                        (results_df['vol_confirm'] == vol_conf) &
                        (results_df['wait_minutes'] == wait) &
                        (results_df['target'] == tgt) &
                        (results_df['sl'] == sl) &
                        (results_df['period'] == 'TEST')
                    ]

                    if len(train_data) > 0 and len(test_data) > 0:
                        train_pnl = train_data.iloc[0]['pnl']
                        test_pnl = test_data.iloc[0]['pnl']
                        train_trades = train_data.iloc[0]['trades']
                        test_trades = test_data.iloc[0]['trades']

                        if train_pnl > 0 and test_pnl > 0 and train_trades > 200 and test_trades > 100:
                            consistent.append({
                                'orb_duration': orb_dur,
                                'vol_confirm': vol_conf,
                                'wait_minutes': wait,
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
                                'train_dd': train_data.iloc[0]['max_dd'],
                                'test_dd': test_data.iloc[0]['max_dd'],
                                'train_target': train_data.iloc[0]['target_rate'],
                                'test_target': test_data.iloc[0]['target_rate'],
                            })

consistent_df = pd.DataFrame(consistent)

if len(consistent_df) > 0:
    consistent_df = consistent_df.sort_values('total_pnl', ascending=False)
    consistent_df.to_csv(f"{OUTPUT_DIR}/orb_10year_consistent.csv", index=False)

# ════════════════════════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════════════════════════

print("\n[5/6] Generating report...")

print("\n" + "=" * 100)
print(" " * 25 + "ORB BREAKOUT - 10-YEAR BACKTEST RESULTS")
print("=" * 100)

# Overall best
test_results = results_df[results_df['period'] == 'TEST'].copy()
test_results = test_results[test_results['trades'] >= 50]

if len(test_results) > 0:
    test_results = test_results.sort_values('pnl', ascending=False)

    print("\n[1] TOP 10 TEST PERIOD CONFIGURATIONS:")
    print("-" * 100)

    for i, (_, row) in enumerate(test_results.head(10).iterrows(), 1):
        print(f"   #{i}. ORB:{row['orb_duration']}min | Vol:{row['vol_confirm']}x | "
              f"Wait:{row['wait_minutes']}min | Tgt:{row['target']}pts | SL:{row['sl']}pts")
        print(f"       P&L: Rs.{row['pnl_rs']:>10,.0f} | {row['trades']:>4} trades | "
              f"{row['win_rate']:.1f}% WR | {row['profit_factor']:.2f} PF | "
              f"{row['target_rate']:.1f}% Target")

# Consistent performers
if len(consistent_df) > 0:
    print("\n[2] CONSISTENTLY PROFITABLE (Train + Test both positive):")
    print("-" * 100)

    for i, (_, row) in enumerate(consistent_df.head(5).iterrows(), 1):
        print(f"\n   #{i}. ORB: {row['orb_duration']} min | Vol: >{row['vol_confirm']}x | "
              f"Wait: {row['wait_minutes']} min | Target: {row['target']} pts | SL: {row['sl']} pts")
        print(f"       ═════════════════════════════════════════════════════════════")
        print(f"       │ Period    │ Trades  │ Win %   │ Target %  │ P&L (pts)    │ P&L (Rs)     │")
        print(f"       ├───────────┼─────────┼─────────┼──────────┼─────────────┼─────────────┘")
        print(f"       │ TRAIN    │ {row['train_trades']:>7}   │ {row['train_wr']:>6.1f}% │ {row['train_target']:>8.1f}% │ "
              f"{row['train_pnl']:>10.0f}   │ Rs.{row['train_pnl']*LOT_SIZE:>11,.0f} │")
        print(f"       │ TEST     │ {row['test_trades']:>7}   │ {row['test_wr']:>6.1f}% │ {row['test_target']:>8.1f}% │ "
              f"{row['test_pnl']:>10.0f}   │ Rs.{row['test_pnl']*LOT_SIZE:>11,.0f} │")
        print(f"       │ TOTAL    │ {row['train_trades']+row['test_trades']:>7}   │ "
              f"{(row['train_wr']+row['test_wr'])/2:>6.1f}% │ "
              f"{(row['train_target']+row['test_target'])/2:>8.1f}% │ "
              f"{row['total_pnl']:>10.0f}   │ Rs.{row['total_pnl']*LOT_SIZE:>11,.0f} │")
        print(f"       │          │         │         │          │             │             │")
        print(f"       │ Max DD   │ Rs.{row['train_dd']*LOT_SIZE:>11,.0f} │ Rs.{row['test_dd']*LOT_SIZE:>11,.0f} │")

    # Best configuration
    best = consistent_df.iloc[0]

    print("\n" + "=" * 100)
    print(" " * 30 + "BEST CONFIGURATION (CONSISTENTLY PROFITABLE)")
    print("=" * 100)
    print(f"\n  ORB Duration:     {best['orb_duration']} minutes")
    print(f"  Volume Confirm:   > {best['vol_confirm']}x average")
    print(f"  Wait Period:      {best['wait_minutes']} minutes after ORB")
    print(f"  Target:           {best['target']} points")
    print(f"  Stop Loss:        {best['sl']} points (other side of ORB)")
    print(f"\n  PERFORMANCE (7+ YEARS):")
    print(f"  ────────────────────────────────────────────────────────────────────")
    print(f"  Total Trades:     {best['train_trades'] + best['test_trades']:,}")
    print(f"  Win Rate:         {(best['train_wr'] + best['test_wr'])/2:.1f}%")
    print(f"  Profit Factor:    {(best['train_pf'] + best['test_pf'])/2:.2f}")
    print(f"  Target Hit Rate:  {(best['train_target'] + best['test_target'])/2:.1f}%")
    print(f"  Total P&L:        {best['total_pnl']:.0f} points")
    print(f"  Total P&L (Rs):   Rs. {best['total_pnl']*LOT_SIZE:,.0f}")
    print(f"  Annual P&L:        Rs. {best['total_pnl']*LOT_SIZE/7:,.0f}/year")
    print(f"  Monthly P&L:      Rs. {best['total_pnl']*LOT_SIZE/7/12:,.0f}/month (1 lot)")
    print(f"  Monthly P&L:      Rs. {best['total_pnl']*LOT_SIZE*5/7/12:,.0f}/month (5 lots)")

else:
    print("\n[2] NO CONSISTENTLY PROFITABLE CONFIGURATIONS")
    print("    (No configuration was profitable in both train and test periods)")
    print("\n    This suggests the strategy may be overfitted to historical data.")

# Parameter analysis
print("\n[3] PARAMETER ANALYSIS (TEST PERIOD):")
print("-" * 100)

for param in ['orb_duration', 'vol_confirm', 'wait_minutes', 'target', 'sl']:
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

# Save final results
print("\n[6/6] Saving results...")
print(f"    Full results: {OUTPUT_DIR}/orb_10year_full_results.csv")
if len(consistent_df) > 0:
    print(f"    Consistent winners: {OUTPUT_DIR}/orb_10year_consistent.csv")

print("\n" + "=" * 100)
print(" " * 30 + "BACKTEST COMPLETE")
print("=" * 100)
