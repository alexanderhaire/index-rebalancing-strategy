#!/usr/bin/env bash
set -e

# 1) Python prep: export mom, rev, and combined PnLs
echo "==> Running Python prep & exporting Python PnLs to python_pnls.csv..."
python << 'PYCODE'
import pandas as pd
from rant import (
    load_events,
    fetch_price_data,
    fetch_fed_funds,
    compute_avg_volume_cap,
    backtest_momentum,
    backtest_reversion,
    simulate
)
from datetime import timedelta

# Load & filter events
events = load_events('Index Add Event Data.xlsx')
start  = events['Announced'].min() - timedelta(days=30)
end    = events['Trade Date'].max()   + timedelta(days=1)

# Fetch data
tickers = events['Ticker'].unique().tolist() + ['SPY']
opens, closes, volume = fetch_price_data(tickers, start, end)
events = events[events['Ticker'].isin(closes.columns)].reset_index(drop=True)

# Compute financing & caps
ff_rates = fetch_fed_funds(start, end)
vol_cap  = compute_avg_volume_cap(volume)

# Compute PnL legs
mom_pnls = backtest_momentum(events, opens, closes, vol_cap, ff_rates)
rev_pnls = backtest_reversion(events, opens, closes, volume, vol_cap)
combined = simulate(events, opens, closes, volume, ff_rates)

# Dump to CSV
pd.DataFrame({
    'mom':       mom_pnls,
    'rev':       rev_pnls,
    'portfolio': combined
}).to_csv('python_pnls.csv', index=False)
PYCODE

# 2) Build rust_input.csv (scores only, dropping NaNs)
echo "==> Exporting Rust input to rust_input.csv..."
python << 'PYCODE'
import pandas as pd
from rant import (
    load_events,
    fetch_price_data,
    fetch_fed_funds,
    compute_avg_volume_cap,
    backtest_momentum,
    backtest_reversion
)
from datetime import timedelta

# Load & filter events
events = load_events('Index Add Event Data.xlsx')
start  = events['Announced'].min() - timedelta(days=30)
end    = events['Trade Date'].max()   + timedelta(days=1)

# Fetch data
tickers = events['Ticker'].unique().tolist() + ['SPY']
opens, closes, volume = fetch_price_data(tickers, start, end)
events = events[events['Ticker'].isin(closes.columns)].reset_index(drop=True)

# Compute financing & caps
ff_rates   = fetch_fed_funds(start, end)
vol_cap    = compute_avg_volume_cap(volume)

# Score events
mom_scores = backtest_momentum(events, opens, closes, vol_cap, ff_rates)
rev_scores = backtest_reversion(events, opens, closes, volume, vol_cap)

# Assemble and drop NaNs
rust_df = events[['Announced','Trade Date','Ticker']].copy()
rust_df['mom_score'] = mom_scores.values
rust_df['rev_score'] = rev_scores.values
rust_df = rust_df.dropna(subset=['mom_score','rev_score'])

# Write Rust input
rust_df.to_csv('rust_input.csv', index=False)
PYCODE

# 3) Run Rust backtester
echo "==> Running Rust backtester..."
./rust_backtester_bin --input rust_input.csv --output rust_output.csv

# 4) Compare Rust vs Python Δ P&L
echo "==> Comparing Rust vs Python Δ P&L..."
python << 'PYCODE'
import pandas as pd
rust = pd.read_csv('rust_output.csv')['pnl']
py   = pd.read_csv('python_pnls.csv')['portfolio']
print((rust - py).describe())
PYCODE

# 5) Compute full Python performance metrics (passing events first)
echo "==> Computing Python performance metrics..."
python << 'PYCODE'
import pandas as pd
from rant import load_events, fetch_price_data
from performance import performance_metrics
from datetime import timedelta

# Reload & filter events
events = load_events('Index Add Event Data.xlsx')
start  = events['Announced'].min() - timedelta(days=30)
end    = events['Trade Date'].max()   + timedelta(days=1)
opens, closes, volume = fetch_price_data(
    events['Ticker'].unique().tolist() + ['SPY'],
    start, end
)
events = events[events['Ticker'].isin(closes.columns)].reset_index(drop=True)

# Load PnL series
df  = pd.read_csv('python_pnls.csv')
mom = df['mom']
rev = df['rev']

# Call with (events, mom_pnls, rev_pnls)
performance_metrics(events, mom, rev)
PYCODE

# 6) Optional visualization
if [ -f visualize.py ]; then
  echo "==> Generating charts..."
  python visualize.py python_pnls.csv rust_output.csv
fi

echo "==> Pipeline complete."
