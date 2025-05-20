Quantitative Strategies Group – Index Rebalancing Strategy
This project fulfills the Quantitative Trader Candidate Project for Quantitative Strategies Group (QSG), showcasing a quantitative trading approach specifically targeting index rebalancing events. It leverages Python and Rust (for cross-validation) to perform backtests, portfolio simulation, and visualize results clearly.

📂 Repository Structure
perl
Copy
Edit
index-rebalancing-strategy/
├── rant.py                   # Core Python logic (feature engineering, model training, backtesting)
├── performance.py            # Python performance evaluation metrics
├── pipeline.sh               # Automation pipeline to run all components easily
├── visualize.py              # Visualizations of cumulative P&L vs. market benchmark (SPY)
├── rust_backtester/          # Rust logic for high-speed backtesting and validation
│   ├── Cargo.toml            # Rust dependencies configuration
│   └── src/
│       └── main.rs           # Rust backtester implementation
├── requirements.txt          # Python dependencies
└── .gitignore                # Git ignored files
⚙️ Installation and Setup
Prerequisites:
Python 3.11

Rust (cargo)

Git

Step-by-Step Install:
bash
Copy
Edit
# Clone the repository
git clone https://github.com/alexanderhaire/index-rebalancing-strategy.git
cd index-rebalancing-strategy

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the Rust backtester
cd rust_backtester
cargo build --release
cp target/release/rust_backtester ../rust_backtester_bin
cd ..

# Set permissions and run the pipeline
chmod +x pipeline.sh
./pipeline.sh
🚀 Pipeline Execution
Running the pipeline (./pipeline.sh) does the following:

Loads index rebalancing events and prepares data (rant.py)

Constructs features, backtests strategies, and trains an XGBoost model

Computes portfolio returns and exports data for Rust validation

Performs Rust-based backtesting and compares with Python results

Generates visual performance charts

📈 Performance Metrics
Your pipeline outputs clear metrics including:

Total cumulative return

Mean and standard deviation of returns

Comparative stats (Python vs. Rust) ensuring validation

Sample terminal output from running pipeline:

yaml
Copy
Edit
==> Computing performance metrics...
Python metrics: {'total_return': -0.0899, 'mean_return': -0.1184, 'std_dev': 0.0575}
Rust metrics:   {'total_return': -0.0899, 'mean_return': -0.1184, 'std_dev': 0.0575}
📊 Visualization
The visualize.py script outputs visual comparisons clearly showcasing cumulative P&L curves for:

Momentum Strategy

Mean Reversion Strategy

Combined ML Strategy

Market Benchmark (SPY ETF)

Visual results saved as:

pnl_strategies_vs_spy.png

📝 Strategy Overview (Detailed in PDF Report)
Your strategy captures the structural alpha from index rebalance events by:

Predicting returns using momentum and mean reversion strategies.

Blending these signals optimally using a trained ML (XGBoost) model.

Validating robustness through Rust-based backtesting.

Detailed descriptions, assumptions, logic, and tradeoffs are found in the submitted project PDF report (index_rebalancing_reportyer.pdf).

🖥️ Reproducibility
This project is fully reproducible using instructions provided. Any differences between Python and Rust performance indicate validation success or necessary debugging clearly identified by delta statistics provided in the pipeline output.

📧 Contact Information
Author: Alexander Haire

GitHub: https://github.com/alexanderhaire

Email: awh20s@fsu.edu

