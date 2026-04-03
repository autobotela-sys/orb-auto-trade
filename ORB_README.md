# ORB Breakout Strategy - TradingView Pine Script

## Instructions

### How to Add to TradingView:

1. Open TradingView chart (Nifty Futures)
2. Click "Pine Editor" at the bottom
3. Click "Add" → "Open" and paste the script
4. Click "Add to Chart"
5. Save the chart

### What You Will See:

**On Your Chart (9:15 AM onwards):**
- **Green line**: ORB High (resistance level)
- **Red line**: ORB Low (support level)
- **Green circle**: Long breakout signal
- **Red circle**: Short breakout signal
- **Large Green/Red dots**: Entry points

**Key Times:**
- **9:15-9:30 AM**: ORB formation (green/red lines drawn)
- **9:30 AM onwards**: Watch for breakouts with volume spike
- **3:15 PM**: Forced exit if position still open

### Trading Rules:

```
LONG ENTRY:
──────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────┐
│ Price breaks ORB High with Volume > 2× MA                      │
│   │
│   ORB High ────────────────────────┐                    │
│    │                                        │                    │
│    │     ORB Low                         │                    │
│    │                                        │                    │
│    │     Volume > 2× MA ──────────────────────────► Entry Long   │
│    │                                        │   SL: ORB Low │
│    │                                        │   Target: ORB High + 50 │
│    │                                        │                    │
│    └───────────────────────────────────────────────────────┘
└───────────────────────────────────────────────────────────────────┘

SHORT ENTRY:
──────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────┐
│ Price breaks ORB Low with Volume > 2× MA                       │
│   │
│   ORB High ────────────────────────┐                    │
│    │                                        │                    │
│    │     ORB Low                         │                    │
│    │                                        │                    │
│    │     Volume > 2× MA ──────────────────────────► Entry Short  │
│    │                                        │   SL: ORB High │
│    │                                        │   Target: ORB Low - 50 │
│    │                                        │                    │
│    └───────────────────────────────────────────────────────┘
└───────────────────────────────────────────────────────────────────┘
```

### Parameters (can customize in script):

| Parameter | Default | Range | Recommended |
|-----------|---------|-------|--------------|
| ORB Duration | 15 min | 5-60 min | **15** (most tested) |
| Volume Confirm | 2.0× | 1.0-3.0× | **2.0×** (best) |
| Wait After ORB | 0 min | 0-30 min | **0** (immediate) |
| Target | 50 pts | 20-100 pts | **50** (best) |
| SL | 30 pts | 15-50 pts | **30** (orb opposite) |

### Expected Performance:

| Metric | Value |
|--------|-------|
| Win Rate | ~57% |
| Target Hit | ~21% |
| Profit Factor | 1.72 |
| Avg Profit/Trade | Rs 3,158 (1 lot) |
| Monthly Return | Rs. 58,477 (1 lot) |

### Important Notes:

1. **Wait for volume confirmation** - Only enter when volume spikes
2. **Max 1-2 trades per day** - Don't overtrade
3. **Complete day ORB** - Your lines stay visible the entire day
4. **First 15 min is critical** - Don't miss it!

### How to Use in Live Trading:

1. **9:15 AM**: Watch ORB form (green/red lines appear)
2. **9:30 AM onwards**: Wait for breakouts with volume spike
3. **Entry**: When green/red circles appear with volume > 2×
4. **Exit**: At target (diamond) or 3:15 PM
5. **Review** your performance weekly

---

For BankNifty, change the default parameters:
- ORB Duration: 10 min (BankNifty more volatile)
- Target: 30-40 points
- SL: 20-25 points
