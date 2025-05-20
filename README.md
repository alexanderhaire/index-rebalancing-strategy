
# Index Rebalancing Strategy

This project presents a quantitative trading strategy focused on **index rebalancing events**. It combines **Python** for feature engineering, modeling, and simulation with **Rust** for high-speed backtesting and cross-validation. The pipeline is modular, reproducible, and includes performance evaluation and visualization tools.

---

## 📂 Repository Structure

```

index-rebalancing-strategy/
├── rant.py                   # Core Python logic (feature engineering, model training, backtesting)
├── performance.py            # Python performance evaluation metrics
├── pipeline.sh               # One-click pipeline to execute entire strategy and backtest
├── visualize.py              # Strategy and benchmark visualization (P\&L curves)
├── rust\_backtester/          # Rust implementation for fast P\&L validation
│   ├── Cargo.toml            # Rust dependency config
│   └── src/
│       └── main.rs           # Rust backtester code
├── requirements.txt          # Python dependencies
├── rust\_backtester\_bin       # Compiled Rust binary
└── .gitignore                # Ignored files and environments

````

---

## ⚙️ Installation & Setup

### Prerequisites:
- Python 3.11+
- Rust (`cargo`)
- Git

### Step-by-Step:

```bash
# 1. Clone the repository
git clone https://github.com/alexanderhaire/index-rebalancing-strategy.git
cd index-rebalancing-strategy

# 2. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Build the Rust backtester
cd rust_backtester
cargo build --release
cp target/release/rust_backtester ../rust_backtester_bin
cd ..

# 4. Run the full pipeline
chmod +x pipeline.sh
./pipeline.sh
````

---

## 🚀 Pipeline Overview

The `./pipeline.sh` script automates the following:

1. Loads and cleans index rebalancing event data from Excel.
2. Performs backtests on momentum and mean-reversion strategies.
3. Trains an XGBoost regression model using engineered features.
4. Simulates portfolio returns based on model-driven allocation.
5. Exports results for Rust-based validation.
6. Runs a Rust P\&L backtester for cross-validation.
7. Generates a chart comparing strategy performance vs. SPY.

---

## 📈 Performance Metrics

The pipeline prints key metrics:

```yaml
Python metrics:
  total_return:    -0.0899
  mean_return:     -0.1184
  std_dev:         0.0575

Rust metrics:
  total_return:    -0.0899
  mean_return:     -0.1184
  std_dev:         0.0575
```

These metrics are calculated over the lifecycle of simulated trades and help benchmark the strategy's risk-adjusted returns.

---

## 📊 Visual Output

The visualization script produces:

* **Cumulative P\&L curves** for:

  * ML Combined strategy
  * Momentum strategy
  * Mean Reversion strategy
  * SPY (benchmark)

Output saved as:
`pnl_strategies_vs_spy.png`

---

## 🧠 Strategy Overview

This strategy captures potential **structural alpha** during index additions by:

* Using **momentum and mean reversion signals** engineered from historical price data.
* Training an **XGBoost model** to weight these signals intelligently.
* Allocating capital across rebalance events based on the ML-predicted alpha.
* Pricing synthetic options using **QuantLib** to simulate real-world overlays.
* Validating P\&L with a **Rust backtester** for performance and correctness.

See the full write-up in:
📄 `index_rebalancing_reportyer.pdf`

---

## 🖥️ Reproducibility

All components (data prep, training, simulation, visualization, and validation) are reproducible through `pipeline.sh`.

Discrepancies between Python and Rust results are printed clearly and aid in debugging or validation QA.

---

## 📧 Contact

* **Author**: Alexander Haire
* **GitHub**: [@alexanderhaire](https://github.com/alexanderhaire)
* **Email**: [awh20s@fsu.edu](mailto:awh20s@fsu.edu)

---

## 📎 Supporting Files

* **Project PDF Report**: [`index_rebalancing_reportyer.pdf`](./index_rebalancing_reportyer.pdf)
* **Code Snapshot**: [`Index_Rebalancing_Code.txt`](./Index_Rebalancing_Code.txt)
* **Candidate Prompt**: [`Quant Trader Candidate Project.pdf`](./Quant%20Trader%20Candidate%20Project.pdf)

---
