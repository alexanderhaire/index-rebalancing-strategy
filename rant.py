import pandas as pd
import numpy as np
import yfinance as yf
import QuantLib as ql
import pandas_datareader.data as web
from datetime import timedelta

# -----------------------------------------------------------------------------
# Constants & Parameters
# -----------------------------------------------------------------------------
PORTFOLIO_VALUE    = 5_000_000       # $5 million gross
TRANSACTION_COST   = 0.01            # $0.01 per share, entry + exit
LONG_SPREAD        = 0.015           # Fed Funds + 1.5% for longs
SHORT_SPREAD       = 0.01            # Fed Funds + 1.0% for shorts
MAX_VOLUME_PCT     = 0.01            # 1% of 20-day average volume
MOM_HOLD_DAYS      = None            # None = exit on trade date close
REV_HOLD_DAYS      = 0               # same-day reversion
FEDFUNDS_SERIES    = 'FEDFUNDS'      # FRED ticker

# -----------------------------------------------------------------------------
# 0) Load & clean the Excel “Data” sheet
# -----------------------------------------------------------------------------
def load_events(path='Index Add Event Data.xlsx') -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=1)
    df['Announced']  = pd.to_datetime(df['Announced'],   errors='coerce')
    df['Trade Date'] = pd.to_datetime(df['Trade Date'], errors='coerce')
    df['Ticker']     = (
        df['Ticker']
        .astype(str)
        .str.replace(r'\s+US$', '', regex=True)
    )
    return df.sort_values('Announced').reset_index(drop=True)

# -----------------------------------------------------------------------------
# 1) Fetch price & volume data (Open, Close, Volume)
# -----------------------------------------------------------------------------
def fetch_price_data(tickers, start, end) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = yf.download(
        tickers,
        start=start,
        end=end + timedelta(days=1),
        progress=False,
        auto_adjust=False
    )
    # extract Open/Close/Volume
    if isinstance(data.columns, pd.MultiIndex):
        opens   = data['Open']
        closes  = data['Close']
        volume  = data['Volume']
    else:
        opens   = data[['Open']]
        closes  = data[['Close']]
        volume  = data[['Volume']]

    # drop tickers without any data
    valid_tix = [t for t in closes.columns if not closes[t].isna().all()]
    opens   = opens[valid_tix]
    closes  = closes[valid_tix]
    volume  = volume[valid_tix]

    return opens, closes, volume

# -----------------------------------------------------------------------------
# 2) Fetch Fed Funds for financing costs
# -----------------------------------------------------------------------------
def fetch_fed_funds(start, end) -> pd.Series:
    ff = web.DataReader(FEDFUNDS_SERIES, 'fred', start, end)
    ff = ff.ffill().bfill() / 100.0   # convert % to decimal
    return ff['FEDFUNDS']

# -----------------------------------------------------------------------------
# 3) Compute 20-day avg volume cap
# -----------------------------------------------------------------------------
def compute_avg_volume_cap(volume: pd.DataFrame) -> pd.DataFrame:
    avg20 = volume.rolling(window=20).mean()
    cap   = (avg20 * MAX_VOLUME_PCT).fillna(0).astype(int)
    return cap

# -----------------------------------------------------------------------------
# 4) Backtest Post-Announcement Momentum (with dailyized financing)
# -----------------------------------------------------------------------------
def backtest_momentum(events: pd.DataFrame,
                      opens: pd.DataFrame,
                      closes: pd.DataFrame,
                      volume_cap: pd.DataFrame,
                      ff_rates: pd.Series) -> pd.Series:

    pnls = []
    n_events = len(events)

    for _, r in events.iterrows():
        ann = r['Announced']
        td  = r['Trade Date']
        tkr = r['Ticker']

        entry_date = ann + timedelta(days=1)
        exit_date  = td

        # skip if no price data for entry/exit date
        if entry_date not in opens.index or exit_date not in closes.index:
            pnls.append(np.nan)
            continue

        entry_price = opens.at[entry_date, tkr]
        exit_price  = closes.at[exit_date,  tkr]

        # skip if still missing
        if pd.isna(entry_price) or pd.isna(exit_price):
            pnls.append(np.nan)
            continue

        # equal-dollar sizing
        allocation = PORTFOLIO_VALUE / n_events
        raw_shares = int(allocation / entry_price)

        # volume cap
        max_shares = volume_cap.at[entry_date, tkr] if tkr in volume_cap.columns else 0
        shares     = min(raw_shares, max_shares)
        if shares <= 0:
            pnls.append(0.0)
            continue

        # raw PnL and costs
        raw_pnl = (exit_price - entry_price) * shares
        tc      = shares * TRANSACTION_COST * 2

        # ---- FIXED FINANCING: convert annual rate to daily ----
        biz_days   = pd.date_range(entry_date, exit_date, freq='B')
        ann_rates  = ff_rates.reindex(biz_days, method='ffill') + LONG_SPREAD
        daily_rate = ann_rates / 252.0
        financing  = entry_price * shares * daily_rate.sum()

        net_pnl = raw_pnl - tc - financing
        pnls.append(net_pnl)

    return pd.Series(pnls, index=events.index)

# -----------------------------------------------------------------------------
# 5) Backtest Event-Day Reversion
# -----------------------------------------------------------------------------
def backtest_reversion(events: pd.DataFrame,
                       opens: pd.DataFrame,
                       closes: pd.DataFrame,
                       volume: pd.DataFrame,
                       volume_cap: pd.DataFrame) -> pd.Series:

    pnls = []
    spy_open  = opens['SPY']
    spy_close = closes['SPY']
    n_events  = len(events)

    for _, r in events.iterrows():
        td  = r['Trade Date']
        tkr = r['Ticker']

        # skip if missing
        if td not in opens.index or td not in closes.index:
            pnls.append(np.nan)
            continue

        entry_price = opens.at[td,  tkr]
        exit_price  = closes.at[td, tkr]
        if pd.isna(entry_price) or pd.isna(exit_price):
            pnls.append(np.nan)
            continue

        # signal: long if underperforms SPY
        stock_ret = (exit_price / entry_price) - 1
        spy_ret   = (spy_close.at[td] / spy_open.at[td]) - 1
        signal    = 1 if stock_ret < spy_ret else -1

        allocation = PORTFOLIO_VALUE / n_events
        raw_shares = int(allocation / entry_price)
        max_shares = volume_cap.at[td, tkr] if tkr in volume_cap.columns else 0
        shares     = min(raw_shares, max_shares)
        if shares <= 0:
            pnls.append(0.0)
            continue

        raw_pnl = signal * (exit_price - entry_price) * shares
        tc      = shares * TRANSACTION_COST * 2
        pnls.append(raw_pnl - tc)

    return pd.Series(pnls, index=events.index)

# -----------------------------------------------------------------------------
# 6) (Optional) Option Pricing via QuantLib (unchanged)
# -----------------------------------------------------------------------------
def price_option(date: pd.Timestamp,
                 spot_price: float,
                 strike_offset: float = 0.02,
                 expiry_days: int = 30) -> float:

    cal = ql.UnitedStates(ql.UnitedStates.NYSE)
    ql.Settings.instance().evaluationDate = ql.Date(
        date.day, date.month, date.year
    )

    strike   = spot_price * (1 + strike_offset)
    maturity = cal.advance(
        ql.Date(date.day, date.month, date.year),
        expiry_days,
        ql.Days
    )
    payoff   = ql.PlainVanillaPayoff(ql.Option.Call, strike)
    exercise = ql.EuropeanExercise(maturity)

    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(spot_price)),
        ql.YieldTermStructureHandle(
            ql.FlatForward(0, cal, 0.0, ql.Actual365Fixed())
        ),
        ql.YieldTermStructureHandle(
            ql.FlatForward(0, cal, 0.01, ql.Actual365Fixed())
        ),
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(0, cal, 0.2, ql.Actual365Fixed())
        )
    )

    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    return option.NPV()

# -----------------------------------------------------------------------------
# 7) Simulate & report combined PnL
# -----------------------------------------------------------------------------
def simulate(events, opens, closes, volume, ff_rates):
    volume_cap = compute_avg_volume_cap(volume)
    mom_pnls   = backtest_momentum(events, opens, closes, volume_cap, ff_rates)
    rev_pnls   = backtest_reversion(events, opens, closes, volume, volume_cap)
    total_pnl  = (mom_pnls.fillna(0) + rev_pnls.fillna(0)).cumsum()
    return total_pnl

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    events = load_events()
    start  = events['Announced'].min() - timedelta(days=30)
    end    = events['Trade Date'].max() + timedelta(days=1)
    tickers = events['Ticker'].unique().tolist() + ['SPY']

    opens, closes, volume = fetch_price_data(tickers, start, end)

    # filter events without data
    valid_mask = events['Ticker'].isin(closes.columns)
    events     = events[valid_mask].reset_index(drop=True)

    ff_rates = fetch_fed_funds(start, end)
    pnl      = simulate(events, opens, closes, volume, ff_rates)

    print("Cumulative PnL:")
    print(pnl.tail(10))
