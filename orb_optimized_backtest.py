"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   ORB BREAKOUT - OPTIMIZED 10-YEAR BACKTEST                       ║
║                   Vectorized for speed                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np

DATA_PATH = r"C:/Users/elamuruganm/Documents/Projects/BT/NiftyData/nifty_futures_1min_2016_2023.csv"
OUTPUT_DIR = r"C:/Users/elamuruganm/Documents/Projects/BT/results"

LOT_SIZE = 50
COST_PER_TRADE = 2.0  # Simplified cost

# Train/Test Split
TRAIN_START = "2016-01-01"
TRAIN_END = "2020-12-31"
TEST_START = "2021-01-01"
TEST_END = "2023-02-28"

print("=" * 100)
print(" " * 25 + "ORB BREAKOUT - OPTIMIZED 10-YEAR BACKTEST")
print("=" * 100)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

print("\n[1/5] Loading data...")
df = pd.read_csv(DATA_PATH)
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df = df.set_index('DateTime')
df = df.between_time('09:15', '15:30')
df = df[~df.index.duplicated(keep='first')]

print(f"    Loaded: {len(df):,} bars")
print(f"    Date range: {df.index[0].date()} to {df.index[-1].date()}")

# Add columns
df['Date'] = df.index.date
df['Year'] = df.index.year
df['Time'] = df.index.hour * 60 + df.index.minute
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

# Split train/test
train_df = df[(df.index >= TRAIN_START) & (df.index <= TRAIN_END)].copy()
test_df = df[(df.index >= TEST_START) & (df.index <= TEST_END)].copy()

print(f"    Train: {len(train_df):,} bars ({train_df.index[0].date()} to {train_df.index[-1].date()})")
print(f"    Test: {len(test_df):,} bars ({test_df.index[0].date()} to {test_df.index[-1].date()})")

# ══════════════════════════════════════════════════════════════════════════════
# BACKTEST FUNCTION (vectorized)
# ══════════════════════════════════════════════════════════════════════════════

print("\n[2/5] Building backtest engine...")

def backtest_orb_vectorized(data, orb_duration, vol_confirm, wait_minutes, target_pts, sl_points):
    """Vectorized ORB backtest"""

    results = []

    # Group by date and calculate ORB
    grouped = data.groupby('Date')

    for date, day_data in grouped:
        # ORB period
        orb_start = 9 * 60 + 15  # 9:15
        orb_end = orb_start + orb_duration

        orb_mask = day_data['Time'] <= orb_end
        orb_data = day_data[orb_mask]

        if len(orb_data) < 5:
            continue

        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_range = orb_high - orb_low

        if orb_range < 5:
            continue

        # Trade period
        trade_start = orb_end + wait_minutes
        trade_mask = day_data['Time'] >= trade_start
        trade_data = day_data[trade_mask]

        if len(trade_data) < 2:
            continue

        # Find breakouts (first occurrence)
        long_breakout = trade_data[trade_data['High'] > orb_high].index
        short_breakout = trade_data[trade_data['Low'] < orb_low].index

        # Process LONG
        if len(long_breakout) > 0:
            entry_time = long_breakout[0]
            entry_idx = day_data.index.get_loc(entry_time)

            # Volume check
            vol_ok = trade_data.loc[entry_time, 'Volume_Ratio'] >= vol_confirm

            if vol_ok or vol_confirm == 1.0:
                entry = orb_high + 0.5
                sl = orb_low
                tgt = entry + target_pts

                # Exit
                exit_price = None
                for j in range(entry_idx + 1, min(entry_idx + 100, len(day_data))):
                    r = day_data.iloc[j]

                    if r['Time'] >= 15 * 60 + 15:
                        exit_price = r['Close']
                        reason = 'Time'
                        break
                    if r['Low'] <= sl:
                        exit_price = sl
                        reason = 'SL'
                        break
                    if r['High'] >= tgt:
                        exit_price = tgt
                        reason = 'Target'
                        break

                if exit_price is None:
                    exit_price = day_data.iloc[min(entry_idx + 99, len(day_data) - 1)]['Close']
                    reason = 'Max Bars'

                pnl = exit_price - entry - COST_PER_TRADE

                results.append({
                    'date': date,
                    'year': entry_time.year,
                    'entry_time': entry_time,
                    'direction': 'LONG',
                    'entry': entry,
                    'exit': exit_price,
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'orb_range': orb_range,
                    'target': target_pts,
                    'sl': sl_points,
                    'gross_pnl': exit_price - entry,
                    'net_pnl': pnl,
                    'reason': reason
                })

        # Process SHORT
        if len(short_breakout) > 0:
            entry_time = short_breakout[0]
            entry_idx = day_data.index.get_loc(entry_time)

            vol_ok = trade_data.loc[entry_time, 'Volume_Ratio'] >= vol_confirm

            if vol_ok or vol_confirm == 1.0:
                entry = orb_low - 0.5
                sl = orb_high
                tgt = entry - target_pts

                # Exit
                exit_price = None
                for j in range(entry_idx + 1, min(entry_idx + 100, len(day_data))):
                    r = day_data.iloc[j]

                    if r['Time'] >= 15 * 60 + 15:
                        exit_price = r['Close']
                        reason = 'Time'
                        break
                    if r['High'] >= sl:
                        exit_price = sl
                        reason = 'SL'
                        break
                    if r['Low'] <= tgt:
                        exit_price = tgt
                        reason = 'Target'
                        break

                if exit_price is None:
                    exit_price = day_data.iloc[min(entry_idx + 99, len(day_data) - 1)]['Close']
                    reason = 'Max Bars'

                pnl = entry - exit_price - COST_PER_TRADE

                results.append({
                    'date': date,
                    'year': entry_time.year,
                    'entry_time': entry_time,
                    'direction': 'SHORT',
                    'entry': entry,
                    'exit': exit_price,
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'orb_range': orb_range,
                    'target': target_pts,
                    'sl': sl_points,
                    'gross_pnl': entry - exit_price,
                    'net_pnl': pnl,
                    'reason': reason
                })

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════════════════════

print("\n[3/5] Running backtests...")

# Test combinations (reduced for speed)
configs = [
    # (ORB duration, vol confirm, wait, target, SL)
    (15, 1.3, 0, 40, 25),
    (15, 1.3, 0, 50, 30),
    (15, 1.5, 0, 40, 25),
    (15, 1.5, 0, 50, 30),
    (15, 2.0, 0, 40, 25),
    (15, 2.0, 0, 50, 30),
    (15, 2.0, 5, 40, 25),
    (15, 2.0, 5, 50, 30),
    (20, 1.5, 0, 40, 25),
    (20, 1.5, 0, 50, 30),
    (20, 2.0, 0, 40, 25),
    (20, 2.0, 5, 50, 30),
    (30, 1.5, 0, 40, 25),
    (30, 1.5, 0, 50, 30),
]

all_results = []

for orb_dur, vol_conf, wait, tgt, sl in configs:
    print(f"    Testing: ORB={orb_dur}min Vol={vol_conf}x Wait={wait}min Tgt={tgt} SL={sl}")

    # Train
    train_trades = backtest_orb_vectorized(train_df, orb_dur, vol_conf, wait, tgt, sl)
    # Test
    test_trades = backtest_orb_vectorized(test_df, orb_dur, vol_conf, wait, tgt, sl)

    for period, trades in [('TRAIN', train_trades), ('TEST', test_trades)]:
        if len(trades) == 0:
            continue

        total = len(trades)
        wins = (trades['net_pnl'] > 0).sum()
        wr = (wins / total * 100) if total > 0 else 0
        pnl = trades['net_pnl'].sum()

        win_trades = trades[trades['net_pnl'] > 0]
        lose_trades = trades[trades['net_pnl'] < 0]
        pf = abs(win_trades['net_pnl'].sum() / lose_trades['net_pnl'].sum()) if lose_trades['net_pnl'].sum() < 0 else 0

        target_hits = (trades['reason'] == 'Target').sum()
        target_rate = (target_hits / total * 100) if total > 0 else 0

        cumul = trades['net_pnl'].cumsum()
        max_dd = (cumul - cumul.cummax()).min()

        all_results.append({
            'orb_duration': orb_dur,
            'vol_confirm': vol_conf,
            'wait_minutes': wait,
            'target': tgt,
            'sl': sl,
            'period': period,
            'trades': total,
            'wins': wins,
            'win_rate': wr,
            'target_rate': target_rate,
            'pnl': pnl,
            'pnl_rs': pnl * LOT_SIZE,
            'profit_factor': pf,
            'max_dd': max_dd,
        })

# ════════════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════════

print("\n[4/5] Generating report...")

results_df = pd.DataFrame(all_results)
Path(OUTPUT_DIR).mkdir(exist_ok=True)
results_df.to_csv(f"{OUTPUT_DIR}/orb_10year_results.csv", index=False)

print("\n" + "=" * 100)
print(" " * 30 + "ORB BREAKOUT - 10-YEAR BACKTEST RESULTS")
print("=" * 100)

# Show TEST results
test_results = results_df[results_df['period'] == 'TEST'].copy()
test_results = test_results.sort_values('pnl', ascending=False)

print(f"\n[1] TEST PERIOD RESULTS ({TEST_START} to {TEST_END}):")
print("-" * 100)
print(f"{'ORB':<6} {'Vol':<6} {'Wait':<6} {'Tgt':<6} {'SL':<6} {'Trades':<8} {'WR%':<8} {'Tgt%':<8} {'P&L (Rs)':<15}")
print("-" * 100)

for _, row in test_results.head(15).iterrows():
    print(f"{row['orb_duration']:<6} {row['vol_confirm']:<6} {row['wait_minutes']:<6} "
          f"{row['target']:<6} {row['sl']:<6} {row['trades']:<8} {row['win_rate']:<8.1f} "
          f"{row['target_rate']:<8.1f} Rs.{row['pnl_rs']:>13,.0f}")

# Consistent performers
train_results = results_df[results_df['period'] == 'TRAIN'].copy()
consistent = []

for _, test_row in test_results.iterrows():
    train_match = train_results[
        (train_results['orb_duration'] == test_row['orb_duration']) &
        (train_results['vol_confirm'] == test_row['vol_confirm']) &
        (train_results['wait_minutes'] == test_row['wait_minutes']) &
        (train_results['target'] == test_row['target']) &
        (train_results['sl'] == test_row['sl'])
    ]

    if len(train_match) > 0:
        train_row = train_match.iloc[0]

        if train_row['pnl'] > 0 and test_row['pnl'] > 0:
            consistent.append({
                'orb_duration': test_row['orb_duration'],
                'vol_confirm': test_row['vol_confirm'],
                'wait_minutes': test_row['wait_minutes'],
                'target': test_row['target'],
                'sl': test_row['sl'],
                'train_pnl': train_row['pnl'],
                'test_pnl': test_row['pnl'],
                'total_pnl': train_row['pnl'] + test_row['pnl'],
                'train_wr': train_row['win_rate'],
                'test_wr': test_row['win_rate'],
                'train_pf': train_row['profit_factor'],
                'test_pf': test_row['profit_factor'],
                'train_trades': train_row['trades'],
                'test_trades': test_row['trades'],
                'train_target': train_row['target_rate'],
                'test_target': test_row['target_rate'],
            })

consistent_df = pd.DataFrame(consistent)

if len(consistent_df) > 0:
    consistent_df = consistent_df.sort_values('total_pnl', ascending=False)
    consistent_df.to_csv(f"{OUTPUT_DIR}/orb_10year_consistent.csv", index=False)

    print(f"\n[2] CONSISTENTLY PROFITABLE: {len(consistent_df)} combinations")
    print("-" * 100)

    for i, row in consistent_df.head(5).iterrows():
        print(f"\n   ORB:{row['orb_duration']}min Vol:{row['vol_confirm']}x Wait:{row['wait_minutes']}min "
              f"Tgt:{row['target']}pts SL:{row['sl']}pts")
        print(f"   ───────────────────────────────────────────────────────────")
        print(f"   {'Period':<10} {'Trades':<10} {'Win %':<10} {'Target %':<12} {'P&L (pts)':<15} {'PF':<10}")
        print(f"   {'TRAIN':<10} {row['train_trades']:<10} {row['train_wr']:<10.1f} {row['train_target']:<12.1f} "
              f"{row['train_pnl']:<15.1f} {row['train_pf']:<10.2f}")
        print(f"   {'TEST':<10} {row['test_trades']:<10} {row['test_wr']:<10.1f} {row['test_target']:<12.1f} "
              f"{row['test_pnl']:<15.1f} {row['test_pf']:<10.2f}")
        print(f"   {'TOTAL':<10} {row['train_trades']+row['test_trades']:<10} "
              f"{(row['train_wr']+row['test_wr'])/2:<10.1f} "
              f"{(row['train_target']+row['test_target'])/2:<12.1f} "
              f"{row['total_pnl']:<15.1f} Rs.{row['total_pnl']*LOT_SIZE:>13,.0f}")

    # Best
    best = consistent_df.iloc[0]

    print("\n" + "=" * 100)
    print("BEST CONFIGURATION:")
    print("=" * 100)
    print(f"\n  ORB Duration:     {best['orb_duration']} minutes")
    print(f"  Volume Confirm:   > {best['vol_confirm']}x")
    print(f"  Wait Period:      {best['wait_minutes']} minutes after ORB")
    print(f"  Target:           {best['target']} points")
    print(f"  Stop Loss:        {best['sl']} points")
    print(f"\n  PERFORMANCE:")
    print(f"  ────────────────────────────────────────────────────────────")
    print(f"  Total Trades:     {best['train_trades'] + best['test_trades']:,}")
    print(f"  Win Rate:         {(best['train_wr'] + best['test_wr'])/2:.1f}%")
    print(f"  Profit Factor:    {(best['train_pf'] + best['test_pf'])/2:.2f}")
    print(f"  Target Hit:       {(best['train_target'] + best['test_target'])/2:.1f}%")
    print(f"  Total P&L:        {best['total_pnl']:.0f} points")
    print(f"  Total P&L (Rs):   Rs. {best['total_pnl']*LOT_SIZE:,.0f}")
    print(f"  Annual P&L:       Rs. {best['total_pnl']*LOT_SIZE/7:,.0f}/year")
    print(f"  Monthly P&L:      Rs. {best['total_pnl']*LOT_SIZE/7/12:,.0f}/month (1 lot)")
    print(f"  Monthly P&L:      Rs. {best['total_pnl']*LOT_SIZE*5/7/12:,.0f}/month (5 lots)")

else:
    print("\n[2] NO CONSISTENTLY PROFITABLE CONFIGURATIONS")

print("\n" + "=" * 100)
print(f"Results saved to: {OUTPUT_DIR}/orb_10year_results.csv")
print("=" * 100)
