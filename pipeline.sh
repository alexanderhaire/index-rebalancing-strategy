#!/usr/bin/env bash
set -e

# 1) Python prep & export rust_input.csv
echo "==> Running Python prep..."
python rant.py

# 1b) Export Python portfolio to CSV
echo "==> Exporting Python portfolio to python_portfolio.csv..."
python << 'PYCODE'
import pandas as pd
from rant import (
    load_events_from_excel, extract_mappings, fetch_price_data,
    backtest_momentum, backtest_reversion, build_features,
    train_ml_model, allocate_capital, simulate_portfolio
)
from datetime import timedelta

# load data & mappings
events  = load_events_from_excel('Index Add Event Data.xlsx')
sectors, adv = extract_mappings(events)

# fetch prices for backtests
tickers = events['Ticker'].unique().tolist()
prices  = fetch_price_data(
    tickers + ['SPY'],
    start=events['Announced'].min() - timedelta(20),
    end=events['Trade Date'].max() + timedelta(20)
)

# compute returns
mom = backtest_momentum(events, prices)
rev = backtest_reversion(events, prices)

# build features & filter invalid labels
feats = build_features(events, prices, sectors, adv)
y     = pd.DataFrame({'mom': mom, 'rev': rev})
y.replace([pd.NA, float('inf'), -float('inf')], pd.NA, inplace=True)
mask = y.notnull().all(axis=1)

events = events.loc[mask].reset_index(drop=True)
feats  = feats.loc[mask].reset_index(drop=True)
mom    = mom.loc[mask].reset_index(drop=True)
rev    = rev.loc[mask].reset_index(drop=True)
y      = y.loc[mask].reset_index(drop=True)

# train & allocate
model     = train_ml_model(feats, y)
alloc     = allocate_capital(model, feats)

# simulate portfolio
portfolio = simulate_portfolio(events, prices, mom, rev, alloc)

# write out Python curve
pd.DataFrame({'portfolio': portfolio}).to_csv('python_portfolio.csv', index=False)
PYCODE

# 1c) Export full price history for Rust
echo "==> Exporting full price history to prices.csv..."
python << 'PYCODE'
import pandas as pd
from rant import load_events_from_excel, fetch_price_data
from datetime import timedelta

events  = load_events_from_excel('Index Add Event Data.xlsx')
tickers = sorted(set(events['Ticker'].tolist() + ['SPY']))

start = events['Announced'].min() - timedelta(20)
end   = events['Trade Date'].max()   + timedelta(20)

prices = fetch_price_data(tickers, start=start, end=end, auto_adjust=False)
prices.to_csv('prices.csv')
PYCODE

# 2) Rust backtest (consume prices.csv & replay Python allocations)
echo "==> Running Rust backtester..."
./rust_backtester_bin --input rust_input.csv --output rust_output.csv


# 3) Quick compare
echo "==> Comparing Rust vs Python Δ P&L..."
python - << 'PYCODE'
import pandas as pd

rust = pd.read_csv('rust_output.csv')['pnl']
py   = pd.read_csv('python_portfolio.csv')['portfolio']
print("Rust vs Python Δ P&L:\n", (rust - py).describe())
PYCODE

# 4) Performance metrics
echo "==> Computing performance metrics..."
python - << 'PYCODE'
import pandas as pd
from performance import performance_metrics

py  = pd.read_csv('python_portfolio.csv')['portfolio']
rus = pd.read_csv('rust_output.csv')['pnl']
print("Python metrics:", performance_metrics(py))
print("Rust   metrics:", performance_metrics(rus))
PYCODE

# 5) Visualizations (optional)
if [ -f visualize.py ]; then
  echo "==> Generating charts..."
  python visualize.py rust_output.csv python_portfolio.csv
fi

echo "==> Pipeline complete."
