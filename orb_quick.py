"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   ORB BREAKOUT - SIMPLIFIED TEST                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np

DATA_PATH = r"C:\Users\elamuruganm\Documents\Projects\BT\NiftyData\nifty_futures_1min_2016_2023.csv"
LOT_SIZE = 50

print("=" * 100)
print(" " * 30 + "ORB BREAKOUT - QUICK TEST")
print("=" * 100)

print("\nLoading 3 years data for speed...")
df = pd.read_csv(DATA_PATH, nrows=800000)  # ~3 years
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df.set_index('DateTime')
df = df.between_time('09:15', '15:30')

print(f"Loaded: {len(df):,} bars")

# Add columns
df['Date'] = df.index.date
df['Time'] = df.index.hour * 60 + df.index.minute
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

print("\nRunning backtests...\n")

# Test configurations
configs = [
    # (ORB duration, Volume confirm, Wait, Target, SL)
    (15, 1.5, 5, 40, 25),
    (15, 1.5, 5, 50, 30),
    (15, 2.0, 0, 40, 25),
    (15, 2.0, 0, 50, 30),
    (30, 1.5, 0, 40, 25),
    (30, 1.5, 0, 50, 30),
    (30, 2.0, 5, 40, 25),
    (30, 2.0, 5, 50, 30),
]

results = []

for orb_dur, vol_conf, wait, target, sl in configs:
    trades = []

    for date, day_data in df.groupby('Date'):
        orb_start = 9 * 60 + 15  # 9:15
        orb_end = orb_start + orb_dur

        orb_data = day_data[day_data['Time'] <= orb_end]
        if len(orb_data) < 5:
            continue

        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_range = orb_high - orb_low

        if orb_range < 5:
            continue

        # Wait period
        trade_start = orb_end + wait
        post_orb = day_data[day_data['Time'] >= trade_start]

        if len(post_orb) < 2:
            continue

        # Find breakouts
        for idx, row in post_orb.iterrows():
            vol_ok = row['Volume_Ratio'] >= vol_conf if not pd.isna(row['Volume_Ratio']) else False

            if not vol_ok and vol_conf > 1:
                continue

            # Long breakout
            if row['High'] > orb_high:
                entry = orb_high + 0.5
                sl_price = orb_low
                tgt_price = entry + target

                # Find exit
                entry_idx = day_data.index.get_loc(idx)
                for j in range(entry_idx + 1, min(entry_idx + 60, len(day_data))):
                    r = day_data.iloc[j]

                    if r['Time'] >= 15 * 60 + 15:
                        exit_p = r['Close']
                        reason = 'Time'
                        break
                    if r['Low'] <= sl_price:
                        exit_p = sl_price
                        reason = 'SL'
                        break
                    if r['High'] >= tgt_price:
                        exit_p = tgt_price
                        reason = 'Target'
                        break
                else:
                    exit_p = day_data.iloc[min(entry_idx + 59, len(day_data) - 1)]['Close']
                    reason = 'Max Bars'

                # Costs ~2 points
                cost = 2.0
                pnl = exit_p - entry - cost
                trades.append({'pnl': pnl, 'reason': reason, 'dir': 'LONG'})
                break  # One trade per day max

            # Short breakout
            elif row['Low'] < orb_low:
                entry = orb_low - 0.5
                sl_price = orb_high
                tgt_price = entry - target

                entry_idx = day_data.index.get_loc(idx)
                for j in range(entry_idx + 1, min(entry_idx + 60, len(day_data))):
                    r = day_data.iloc[j]

                    if r['Time'] >= 15 * 60 + 15:
                        exit_p = r['Close']
                        reason = 'Time'
                        break
                    if r['High'] >= sl_price:
                        exit_p = sl_price
                        reason = 'SL'
                        break
                    if r['Low'] <= tgt_price:
                        exit_p = tgt_price
                        reason = 'Target'
                        break
                else:
                    exit_p = day_data.iloc[min(entry_idx + 59, len(day_data) - 1)]['Close']
                    reason = 'Max Bars'

                cost = 2.0
                pnl = entry - exit_p - cost
                trades.append({'pnl': pnl, 'reason': reason, 'dir': 'SHORT'})
                break

    if trades:
        trades_df = pd.DataFrame(trades)
        total = len(trades_df)
        wins = (trades_df['pnl'] > 0).sum()
        wr = (wins / total * 100)
        pnl = trades_df['pnl'].sum()

        win_df = trades_df[trades_df['pnl'] > 0]
        lose_df = trades_df[trades_df['pnl'] < 0]
        pf = abs(win_df['pnl'].sum() / lose_df['pnl'].sum()) if lose_df['pnl'].sum() < 0 else 0

        tgt_rate = (trades_df['reason'] == 'Target').sum() / total * 100

        results.append({
            'orb_dur': orb_dur,
            'vol': vol_conf,
            'wait': wait,
            'tgt': target,
            'sl': sl,
            'trades': total,
            'wr': wr,
            'tgt_rate': tgt_rate,
            'pnl': pnl,
            'pf': pf
        })

        print(f"ORB:{orb_dur}min Vol:{vol_conf}x Wait:{wait} Tgt:{target} SL:{sl} | "
              f"{total:4} trades | {wr:5.1f}% WR | {tgt_rate:5.1f}% Tgt | "
              f"P&L: {pnl:8.0f} pts | PF: {pf:.2f}")

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

if results:
    res_df = pd.DataFrame(results)

    print(f"\n{'ORB':<6} {'Vol':<6} {'Wait':<6} {'Tgt':<6} {'SL':<6} {'Trades':<8} {'WR%':<8} {'Tgt%':<8} {'P&L':<12} {'PF':<8}")
    print("-" * 100)

    for _, r in res_df.iterrows():
        print(f"{r['orb_dur']:<6} {r['vol']:<6} {r['wait']:<6} {r['tgt']:<6} {r['sl']:<6} "
              f"{r['trades']:<8} {r['wr']:<8.1f} {r['tgt_rate']:<8.1f} {r['pnl']:<12.0f} {r['pf']:<8.2f}")

    best = res_df.loc[res_df['pnl'].idxmax()]

    print("\n" + "=" * 100)
    print("BEST CONFIGURATION:")
    print(f"  ORB Duration: {best['orb_dur']} minutes")
    print(f"  Volume Confirm: > {best['vol']}x")
    print(f"  Wait: {best['wait']} minutes")
    print(f"  Target: {best['tgt']} points")
    print(f"  Stop Loss: {best['sl']} points")
    print(f"\n  Trades: {int(best['trades'])}")
    print(f"  Win Rate: {best['wr']:.1f}%")
    print(f"  Target Hit: {best['tgt_rate']:.1f}%")
    print(f"  Profit Factor: {best['pf']:.2f}")
    print(f"  P&L: {best['pnl']:.0f} points (Rs. {best['pnl']*LOT_SIZE:,.0f})")

    if best['pnl'] > 0:
        print(f"\n  PROFITABLE! Annualized: Rs. {best['pnl']*LOT_SIZE*3.5:,.0f}")
    else:
        print(f"\n  NOT PROFITABLE")

print("\n" + "=" * 100)
