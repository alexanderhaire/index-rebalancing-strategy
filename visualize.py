import sys
import pandas as pd
import matplotlib.pyplot as plt


def main():
    # Expect two arguments: Python and Rust PnL CSVs
    if len(sys.argv) < 3:
        print("Usage: python visualize.py python_pnls.csv rust_output.csv")
        sys.exit(1)
    py_file, rust_file = sys.argv[1], sys.argv[2]

    # Load PnL series
    py_df   = pd.read_csv(py_file)
    rust_df = pd.read_csv(rust_file)

    # Plot combined equity curves
    plt.figure(figsize=(10, 6))
    plt.plot(py_df['portfolio'].cumsum(), label='Python Combined')
    plt.plot(rust_df['pnl'].cumsum(), '--', label='Rust Combined')
    plt.title('Combined Equity Curve: Python vs Rust')
    plt.xlabel('Event Number')
    plt.ylabel('Cumulative PnL')
    plt.legend()
    plt.tight_layout()
    plt.savefig('combined_equity_curve.png')
    plt.close()

    # Attempt to load price history for SPY
    try:
        price_hist = pd.read_csv('prices.csv', parse_dates=['Date'])
        # Pivot if DataFrame is in long format
        if {'Date', 'Ticker', 'Close'}.issubset(price_hist.columns):
            close = price_hist.pivot(index='Date', columns='Ticker', values='Close')
        else:
            close = price_hist

        if 'SPY' in close.columns:
            spy = close['SPY'].pct_change().cumsum().ffill()
            plt.figure(figsize=(10, 4))
            plt.plot(spy, label='SPY Cumulative')
            plt.title('SPY Cumulative Returns')
            plt.xlabel('Date')
            plt.ylabel('Cumulative Return')
            plt.legend()
            plt.tight_layout()
            plt.savefig('spy_cumulative_returns.png')
            plt.close()
        else:
            print("Warning: 'SPY' not found in price history; skipping SPY chart.")
    except FileNotFoundError:
        print("Warning: prices.csv not found; skipping SPY chart.")

    print("Charts saved: combined_equity_curve.png")
    if 'spy' in locals():
        print("Charts saved: spy_cumulative_returns.png")


if __name__ == '__main__':
    main()
