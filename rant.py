import pandas as pd
import numpy as np
import yfinance as yf
import QuantLib as ql
from datetime import timedelta
from xgboost import XGBRegressor

# Step 0: Load & clean the Excel “Data” sheet
def load_events_from_excel(path='Index Add Event Data.xlsx') -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=1)
    df['Announced']  = pd.to_datetime(df['Announced'],   errors='coerce')
    df['Trade Date'] = pd.to_datetime(df['Trade Date'], errors='coerce')

    def clean(series, regex, percent=False):
        s = series.astype(str).str.replace(regex, '', regex=True)
        num = pd.to_numeric(s, errors='coerce').fillna(0.0)
        return num.div(100.0) if percent else num

    df['Last Px']      = clean(df['Last Px'],      r'[$,]')
    df['Shs to Trade'] = clean(df['Shs to Trade'], r'[^\d]').astype(int)
    df['$MM to Trade'] = clean(df['$MM to Trade'], r'[$,]')
    df['ADV to Trade'] = clean(df['ADV to Trade'], r'[%]', percent=True)
    df['Ticker']       = df['Ticker'].astype(str).str.replace(r'\s+US$', '', regex=True)

    return df.sort_values('Announced').reset_index(drop=True)

# Step 1: Extract sector & ADV mappings
def extract_mappings(events: pd.DataFrame):
    sectors = events.set_index('Ticker')['Sector']
    adv     = events.set_index('Ticker')['ADV to Trade']
    return sectors, adv

# Step 2: Fetch price data and log missing tickers
def fetch_price_data(tickers, start, end, auto_adjust=False) -> pd.DataFrame:
    data = yf.download(tickers, start=start, end=end,
                       progress=False, auto_adjust=auto_adjust)
    # pick closing prices
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Adj Close'] if 'Adj Close' in data.columns.levels[0] else data['Close']
    else:
        if 'Adj Close' in data.columns:
            df = data['Adj Close']
        elif 'Close' in data.columns:
            df = data['Close']
        else:
            df = data.copy()

    # ensure DataFrame
    if isinstance(df, pd.Series):
        df = df.to_frame()

    available = df.columns.tolist()
    missing = [t for t in tickers if t not in available]
    if missing:
        print("⚠️ Missing price data for:", missing)
    return df

# Step 3: Option pricing via QuantLib
def price_option(date: pd.Timestamp, spot_price: float,
                 strike_offset: float = 0.02, expiry_days: int = 30) -> float:
    cal = ql.UnitedStates(ql.UnitedStates.NYSE)
    ql.Settings.instance().evaluationDate = ql.Date(date.day, date.month, date.year)

    strike   = spot_price * (1 + strike_offset)
    maturity = cal.advance(ql.Date(date.day, date.month, date.year), expiry_days, ql.Days)
    payoff   = ql.PlainVanillaPayoff(ql.Option.Call, strike)
    exercise = ql.EuropeanExercise(maturity)

    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(spot_price)),
        ql.YieldTermStructureHandle(ql.FlatForward(0, cal, 0.0, ql.Actual365Fixed())),
        ql.YieldTermStructureHandle(ql.FlatForward(0, cal, 0.01, ql.Actual365Fixed())),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(0, cal, 0.2, ql.Actual365Fixed()))
    )

    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    return option.NPV()

# Step 4: Simple backtests
def backtest_momentum(events, prices):
    rets = []
    for _, r in events.iterrows():
        ann, td, t = r['Announced'], r['Trade Date'], r['Ticker']
        try:
            entry = prices.at[ann + timedelta(days=1), t]
            exit_ = prices.at[td, t]
            rets.append((exit_ - entry) / entry)
        except Exception:
            rets.append(np.nan)
    return pd.Series(rets, index=events.index)

def backtest_reversion(events, prices, hold_days=3):
    rets = []
    for _, r in events.iterrows():
        td, t = r['Trade Date'], r['Ticker']
        try:
            entry = prices.at[td, t]
            exit_ = prices.at[td + timedelta(days=hold_days), t]
            rets.append((entry - exit_) / entry)
        except Exception:
            rets.append(np.nan)
    return pd.Series(rets, index=events.index)

# Step 5: Feature engineering
def build_features(events, prices, sectors, adv):
    feats = pd.DataFrame(index=events.index)
    feats['days_to_trade'] = (events['Trade Date'] - events['Announced']).dt.days

    vol = prices.pct_change().rolling(10).std()
    feats['volatility'] = [
        vol.at[dt, t] if dt in vol.index and t in vol.columns else 0
        for dt, t in zip(events['Announced'], events['Ticker'])
    ]

    one_hot = pd.get_dummies(sectors).reindex(events['Ticker']).set_index(events.index).fillna(0)
    feats = feats.join(one_hot)
    feats['adv_pct'] = events['ADV to Trade']

    ma5 = prices.pct_change().rolling(5).mean()
    feats['ma5'] = [
        ma5.at[dt, t] if dt in ma5.index and t in ma5.columns else 0
        for dt, t in zip(events['Announced'], events['Ticker'])
    ]

    vix = fetch_price_data(
        ['^VIX'],
        start=events['Announced'].min() - timedelta(20),
        end=events['Trade Date'].max() + timedelta(20),
        auto_adjust=False
    )
    vix_ser = vix['^VIX'] if '^VIX' in vix.columns else vix.iloc[:,0]
    feats['vix10'] = [vix_ser.rolling(10).mean().get(dt, 0) for dt in events['Announced']]

    return feats.fillna(0)

# Step 6: Train XGBoost model
def train_ml_model(features, targets):
    model = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05)
    model.fit(features, targets)
    return model

# Step 7: Capital allocation with caps & costs
def allocate_capital(model, features, cost_per_trade=0.0005, max_pos=0.1):
    preds = model.predict(features)
    df    = pd.DataFrame(preds, index=features.index, columns=['mom','rev'])
    alloc = df.div(df.sum(axis=1), axis=0).clip(upper=max_pos)
    return alloc.sub(cost_per_trade).clip(lower=0)

# Step 8: Simulate portfolio P&L
def simulate_portfolio(events, prices, mom_ret, rev_ret, alloc):
    pnl = []
    for idx, r in events.iterrows():
        t, td = r['Ticker'], r['Trade Date']
        try:
            base = alloc.at[idx,'mom'] * mom_ret.at[idx] + alloc.at[idx,'rev'] * rev_ret.at[idx]
            opt  = price_option(td, prices.at[td, t])
            pnl.append(base + (opt / prices.at[td, t]) * 0.01)
        except Exception:
            pnl.append(0)
    return pd.Series(pnl, index=events.index).cumsum()

# Step 9: Export for Rust backtester
def export_for_rust(events, prices, alloc, out_path='rust_input.csv'):
    df = events[['Announced','Trade Date','Ticker']].copy()
    df = df.join(alloc.rename(columns={'mom':'mom_score','rev':'rev_score'}))
    df['price'] = [
        prices.at[r['Announced'], r['Ticker']]
        if r['Announced'] in prices.index and r['Ticker'] in prices.columns else 0
        for _, r in events.iterrows()
    ]
    df.to_csv(out_path, index=False)
    print(f"Exported to {out_path}")

# Main execution
if __name__ == "__main__":
    events = load_events_from_excel()
    sectors, adv = extract_mappings(events)

    # Initial ticker list
    tickers = events['Ticker'].unique().tolist()

    # 1) Fetch full price history to identify available tickers
    all_prices = fetch_price_data(
        tickers + ['SPY'],
        start=events['Announced'].min() - timedelta(20),
        end=events['Trade Date'].max() + timedelta(20),
        auto_adjust=False
    )

    # 2) Filter to only tickers with data
    available = all_prices.columns.tolist()
    available_tickers = [t for t in tickers if t in available]
    print("✅ Using tickers:", available_tickers)

    # (Optional) save valid tickers
    with open('valid_tickers.txt','w') as f:
        for t in available_tickers:
            f.write(t + "\n")

    # 3) Subset price DataFrame
    prices = all_prices[available_tickers + ['SPY']]

    # Run backtests, features, model, simulation
    mom   = backtest_momentum(events, prices)
    rev   = backtest_reversion(events, prices)
    feats = build_features(events, prices, sectors, adv)

    y = pd.DataFrame({'mom': mom, 'rev': rev}).replace([np.inf, -np.inf], np.nan)
    mask = y.notnull().all(axis=1)

    events = events.loc[mask].reset_index(drop=True)
    feats  = feats.loc[mask].reset_index(drop=True)
    mom    = mom.loc[mask].reset_index(drop=True)
    rev    = rev.loc[mask].reset_index(drop=True)
    y      = y.loc[mask].reset_index(drop=True)

    print(f"Training on {len(y)} events after dropping invalid labels.")
    model     = train_ml_model(feats, y)
    alloc     = allocate_capital(model, feats)
    portfolio = simulate_portfolio(events, prices, mom, rev, alloc)

    try:
        from performance import performance_metrics
        print("Metrics:", performance_metrics(portfolio))
    except ImportError:
        print("performance.py not found; skipping metrics.")

    export_for_rust(events, prices, alloc)
