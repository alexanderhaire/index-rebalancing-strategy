import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

def main():
    # 1) Load the Python & Rust P&L series
    df_py   = pd.read_csv('python_portfolio.csv')  # column: 'portfolio'
    df_rust = pd.read_csv('rust_output.csv')       # column: 'pnl'
    combined = df_py['portfolio'].ffill()
    rust     = df_rust['pnl'].ffill()

    # 2) Load the Trade Dates from your events sheet for the x-axis
    events = pd.read_excel('Index Add Event Data.xlsx', sheet_name=1, usecols=['Trade Date'])
    dates = pd.to_datetime(events['Trade Date'])
    # If lengths don’t match, fall back to integer index
    if len(dates) != len(combined):
        dates = pd.RangeIndex(len(combined))

    # 3) Load SPY price history and compute cumulative return at those dates
    prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)
    spy = prices['SPY'].pct_change().cumsum().ffill()
    try:
        spy_on_events = spy.reindex(dates).reset_index(drop=True)
    except Exception:
        spy_on_events = spy.iloc[:len(combined)].reset_index(drop=True)

    # 4) Plot everything
    plt.figure(figsize=(10, 6))
    plt.plot(dates, combined, '--', label='ML Combined', linewidth=2)
    plt.plot(dates, rust,     '-',  label='Rust Backtest',   linewidth=2)
    plt.plot(dates, spy_on_events, ':',  label='SPY Cumulative',   linewidth=2)

    plt.title('Cumulative Returns: ML Strategy vs. Rust Backtest vs. SPY')
    plt.xlabel('Trade Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('pnl_strategies_vs_spy.png')
    plt.show()

if __name__ == "__main__":
    main()
