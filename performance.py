# performance.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
PORTFOLIO_VALUE = 5_000_000    # $5 million gross portfolio
TRADING_DAYS    = 252          # Approximate trading days per year

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------
def max_drawdown(cum_series: pd.Series) -> float:
    peak = cum_series.cummax()
    drawdown = (cum_series - peak) / peak
    return drawdown.min()

def get_metrics(returns: pd.Series) -> dict:
    r = returns.dropna()
    if len(r) == 0:
        return {k: np.nan for k in [
            "Annualized Return", "Volatility",
            "Sharpe Ratio", "Sortino Ratio",
            "Max Drawdown", "Calmar Ratio"
        ]}

    cum = (1 + r).cumprod() - 1
    total_ret = cum.iloc[-1]
    periods   = len(r)
    ann_ret   = (1 + total_ret) ** (TRADING_DAYS / periods) - 1
    vol       = r.std() * np.sqrt(TRADING_DAYS)
    sharpe    = (r.mean() / r.std()) * np.sqrt(TRADING_DAYS) if r.std() != 0 else np.nan

    neg_r        = r[r < 0]
    downside_vol = neg_r.std() * np.sqrt(TRADING_DAYS) if len(neg_r) > 0 else np.nan
    sortino      = (r.mean() / downside_vol) if downside_vol and downside_vol != 0 else np.nan

    mdd    = max_drawdown(cum)
    calmar = ann_ret / abs(mdd) if mdd < 0 else np.nan

    return {
        "Annualized Return": ann_ret,
        "Volatility":       vol,
        "Sharpe Ratio":     sharpe,
        "Sortino Ratio":    sortino,
        "Max Drawdown":     mdd,
        "Calmar Ratio":     calmar
    }

# -----------------------------------------------------------------------------
# Main performance function
# -----------------------------------------------------------------------------
def performance_metrics(
    events: pd.DataFrame,
    mom_pnls: pd.Series,
    rev_pnls: pd.Series
) -> None:
    n_events       = len(events)
    alloc_per_evt  = PORTFOLIO_VALUE / n_events

    mom_ret  = mom_pnls / alloc_per_evt
    rev_ret  = rev_pnls / alloc_per_evt
    comb_ret = mom_ret + rev_ret

    strategies = {
        "Momentum":  mom_ret,
        "Reversion": rev_ret,
        "Combined":  comb_ret
    }

    # 1) Overall
    overall = []
    for name, ret in strategies.items():
        mets = get_metrics(ret)
        mets["Strategy"] = name
        overall.append(mets)
    overall_df = pd.DataFrame(overall).set_index("Strategy")
    print("\n=== Overall Performance ===")
    print(overall_df)

    # 2) By index
    for idx in events["Index"].unique():
        mask    = events["Index"] == idx
        segment = []
        for name, ret in strategies.items():
            mets = get_metrics(ret[mask])
            mets["Strategy"] = name
            segment.append(mets)
        seg_df = pd.DataFrame(segment).set_index("Strategy")
        print(f"\n=== Performance for index: {idx} ===")
        print(seg_df)

    # 3) Equity curves
    plt.figure(figsize=(10, 6))
    for name, ret in strategies.items():
        eq = (1 + ret).cumprod()
        plt.plot(eq, label=name)
    plt.title("Equity Curves by Strategy")
    plt.xlabel("Event Number")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.tight_layout()
    plt.show()

# -----------------------------------------------------------------------------
# If run as a script, execute the full pipeline
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import timedelta
    from rant import (
        load_events,
        fetch_price_data,
        compute_avg_volume_cap,
        fetch_fed_funds,
        backtest_momentum,
        backtest_reversion
    )

    # 1) Load event data
    events = load_events('Index Add Event Data.xlsx')

    # 2) Define date range
    start   = events['Announced'].min() - timedelta(days=30)
    end     = events['Trade Date'].max() + timedelta(days=1)
    tickers = events['Ticker'].unique().tolist() + ['SPY']

    # 3) Fetch OHLCV
    opens, closes, volume = fetch_price_data(tickers, start, end)

    # 4) Filter out events with no data
    valid_mask = events['Ticker'].isin(closes.columns)
    events     = events[valid_mask].reset_index(drop=True)

    # 5) Fetch Fed Funds for financing costs
    ff_rates = fetch_fed_funds(start, end)

    # 6) Compute 1% of 20-day avg. volume caps
    volume_cap = compute_avg_volume_cap(volume)

    # 7) Run both backtests
    mom_pnls = backtest_momentum(events, opens, closes, volume_cap, ff_rates)
    rev_pnls = backtest_reversion(events, opens, closes, volume, volume_cap)

    # 8) Print metrics & show plots
    performance_metrics(events, mom_pnls, rev_pnls)
