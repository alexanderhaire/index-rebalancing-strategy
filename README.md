Great. I’ll prepare a professional `README.md` file for your GitHub repository that documents your Quantitative Trading Strategy Pipeline. It will include an overview, architecture, setup instructions, usage details, and descriptions of each major code component.

I’ll let you know as soon as the draft is ready.


# Quantitative Trading Strategy Pipeline

**A hybrid Python/Rust backtesting pipeline for momentum and mean-reversion strategies on index rebalancing events.** This project provides a comprehensive system to backtest trading strategies around index addition events (e.g., stocks being added to S\&P indices). It combines Python for data handling and analysis with Rust for high-performance backtesting, ensuring accuracy and speed. The pipeline loads historical index event data, simulates trades for two strategies (post-announcement momentum and event-day reversion), and outputs performance metrics and charts.

## Project Overview

This repository automates the analysis of index rebalancing (addition) events to evaluate two trading strategies: **Post-Announcement Momentum** and **Event-Day Reversion**. In the momentum strategy, the pipeline simulates buying (or selling) a stock at the opening price *after* an index-addition announcement and exiting before or on the index inclusion date. In the reversion strategy, it simulates trading on the actual index inclusion day (e.g., shorting stocks that outperform the market and buying those that underperform, aiming for mean reversion). Both strategies are executed with realistic constraints – for example, using a fixed \$5,000,000 portfolio, applying a transaction cost of \$0.01 per share, and accounting for overnight financing costs (Fed Funds rate + 1.5% for longs, +1% for shorts, with no offsetting between positions). The overall goal is to showcase a robust backtesting workflow that **loads data, runs strategy logic in Python, verifies results with a Rust engine, and produces analytical outputs**.

**Key Features:**

* **Hybrid Architecture:** Python handles data ingestion, calculations, and visualization, while Rust provides a fast, compiled backtest engine to replicate the strategies for validation and performance.
* **Momentum & Reversion Strategies:** Built-in support for two trading strategies around index additions, which can be extended or modified. The pipeline easily accommodates different holding periods (from next-day exit up to several weeks) and can integrate hedging (e.g., using SPY as a benchmark or hedge asset).
* **Realistic Trading Assumptions:** Incorporates real-world trading considerations such as portfolio size limits, transaction costs, slippage (approximated via cost per share), liquidity constraints (e.g., limiting position size relative to 20-day average volume), and overnight carry costs using actual interest rates (fetched from the Federal Reserve’s FRED database via `pandas_datareader`).
* **Automated Analysis Outputs:** After running a backtest, the pipeline generates comprehensive performance metrics (e.g. total return, Sharpe ratio, drawdowns, win/loss rates) for each strategy and a combined portfolio. It also produces charts for equity curves and compares strategy performance against the S\&P 500 benchmark (SPY), giving a clear visual representation of results.

## Architecture

The pipeline follows a **step-by-step process** to ensure data integrity and result verification across the Python and Rust implementations. Below is an overview of the workflow:

1. **Data Ingestion (Excel):** The process starts by loading the index event dataset from an Excel file (e.g. **`Index Add Event Data.xlsx`**). This Excel file contains historical index addition events (for indices like S\&P 400, 500, 600), including columns such as the stock ticker, the announcement date of the addition, and the effective date (trade date) when the stock is added to the index. The Python script parses this file into a structured format (using pandas) for further processing.
2. **Market Data Collection:** For each event in the dataset, the pipeline fetches historical market data required for backtesting. This includes daily prices (open, close, high, low) and volumes for the affected stock (and potentially related index or benchmark data). Data is retrieved via the Yahoo Finance API using the `yfinance` library. In addition, reference data like interest rates (e.g. Federal Funds Rate) is pulled using `pandas_datareader` (to compute financing costs). All data is aligned properly with event dates — for example, ensuring we have the price on the day after announcement (for momentum entry) and prices around the index inclusion date.
3. **Python Strategy Backtest (PnL Calculation):** Using the event and price data, the pipeline computes the **P\&L (profit and loss)** for each strategy in Python. The core logic resides in the `rant.py` script, which applies the strategy rules to each event:

   * For the **Momentum strategy**, it simulates entering a position at the next market open after the announcement date and exiting the position at a specified time (e.g., the close of the day before the inclusion, or another exit rule).
   * For the **Reversion strategy**, it simulates trades on the inclusion day: e.g., if the stock’s return on that day exceeds the market’s return, short the stock (or if it underperforms, go long), then exit after a short holding period (such as end-of-day or next day).

   The Python backtest accounts for **transaction costs** (`$0.01/share`) for each entry and exit, and **overnight financing costs** for multi-day holds (using daily interest rates from FRED: Fed Funds + 1.5% for long positions, +1% for shorts). These financing costs are applied for each day a position is held overnight. The result of this step is a series of cash flows or daily PnL values for each strategy and each event. The script then aggregates these into cumulative PnL or returns for the entire backtest period for each strategy. Intermediate results (like per-event PnL or daily returns) are stored in pandas DataFrames.
4. **Export & Handoff to Rust:** After the Python calculation, the pipeline exports relevant data to CSV files so that the Rust component can ingest it. For example, `rant.py` may output a CSV summarizing each trade or daily PnL timeline (with fields like event ID, dates, positions, and PnL). This ensures the Rust backtester works with the exact same input data and assumptions as the Python version. The CSV export acts as an interface between the Python and Rust parts of the pipeline.
5. **Rust Backtester Execution:** The compiled Rust binary (***`rust_backtester_bin`***) is then run (via the Bash script) to perform an independent backtest using the same event data and strategy logic. The Rust program is implemented to mirror the strategy rules applied in Python – it reads the input (either the original event Excel or the CSV outputs from Python) and recomputes the momentum and reversion strategy PnL. Rust’s strong type safety and performance ensure that this step can handle large datasets efficiently and serves as a **validation** of the Python results. The Rust backtester outputs its own calculations of strategy PnL, typically writing results to its own CSV files or standard output.
6. **Result Comparison (Python vs Rust):** Once the Rust run is complete, the pipeline compares the outcomes from Python and Rust. This step verifies that both implementations yield consistent results. Any discrepancies can be flagged for further investigation. In practice, the pipeline might load the CSV output from Rust and the CSV from Python into pandas and compute differences. Ideally, the cumulative PnL curves and trade-by-trade results from the two should match closely (allowing for any minor differences due to rounding). This cross-check increases confidence in the correctness of the backtest results.
7. **Performance Metrics & Reporting:** Next, the pipeline computes overall performance metrics for each strategy and the combined portfolio. The `performance.py` script takes the PnL time series and calculates key metrics such as:

   * **Total Return** and **CAGR (Compound Annual Growth Rate)** for the period,
   * **Volatility** (standard deviation of returns),
   * **Sharpe Ratio** (risk-adjusted return, using a suitable risk-free rate),
   * **Max Drawdown** (the largest peak-to-trough equity decline),
   * **Win Rate** (percentage of profitable events/trades), and more.

   These statistics provide a quantitative summary of how each strategy performed. For example, it might show that the momentum strategy achieved X% total return with a Sharpe of Y, versus the reversion strategy’s Z% return. The metrics help in understanding whether either strategy has an edge and how they compare to a benchmark (like simply holding the S\&P 500).
8. **Visualization (Charts Generation):** Finally, the `visualize.py` script produces charts to aid in analysis. It uses `matplotlib` to plot **equity curves** for each strategy and the combined strategy, as well as to compare strategy performance against **benchmark** performance (e.g., the SPY ETF). These visuals include:

   * Cumulative return curves for the Momentum vs Reversion strategies (and their combination) across the sequence of events.
   * A comparison of the **combined strategy PnL vs. the Rust backtester’s PnL** (to visually confirm that the Python and Rust implementations match).
   * The **benchmark (SPY) cumulative return** over the same period, to contextualize strategy performance versus the broad market.
   * Potentially, bar charts or distribution plots of per-trade returns or other insightful visualizations.

   All charts are saved as PNG files in an output directory for review. This step is optional and can be toggled – for instance, in a headless environment you might skip chart generation, but when analyzing results, these charts provide valuable intuition.

## Technology Stack

This project leverages a mix of technologies to achieve both ease of development and execution speed:

* **Python 3.x** – Used for data processing, strategy logic implementation, and analytics. Key libraries include:

  * **pandas** for data manipulation (loading Excel, managing time series of prices and PnL).
  * **yfinance** for pulling historical stock price and volume data from Yahoo Finance.
  * **pandas\_datareader** for fetching macro data (e.g., interest rates from FRED).
  * **QuantLib** for advanced financial calculations (used here primarily to handle interest rate calculations for financing costs, though also capable of much more).
  * **matplotlib** (with **matplotlib.pyplot**) for generating plots and charts of performance.
* **Rust 1.xx** – Used to implement the backtesting engine in a compiled language. The Rust code (organized as a Cargo project) produces a binary `rust_backtester_bin`. Rust brings performance and type safety; it can handle computations on large datasets faster than pure Python and helps validate the Python results. The Rust implementation likely uses crates such as `csv` (for reading data exported from Python) and possibly `reqwest` or an API client if it fetched data directly (though in this pipeline it primarily consumes prepared data).
* **Bash** – The pipeline is orchestrated by a shell script (`pipeline.sh`), which automates the sequence of steps. The script ensures the Python virtual environment is activated, runs the Python scripts in order, triggers the Rust binary, and ties all outputs together. This makes it easy to run the entire pipeline with a single command.
* **Data Sources**: Historical price data comes from **Yahoo Finance** (via `yfinance`), which provides daily OHLCV data. Interest rate data (for financing calculations) comes from the **Federal Reserve Economic Data (FRED)** via `pandas_datareader`. The input event dataset is an **Excel spreadsheet**, which the user must provide (not included due to data licensing) – this contains the list of index additions to backtest.
* **Environment**: The project is cross-platform. Development was done on a Unix-like environment (Linux/Mac), with a Python virtual environment for dependencies and Rust’s Cargo for building the binary. Windows users can also run the pipeline, though the `pipeline.sh` script may need a Bash shell (or adapt the commands for PowerShell).

## Setup Instructions

To set up the project locally, follow these steps:

### 1. Clone the Repository

First, clone this GitHub repository to your local machine:

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

### 2. Python Virtual Environment and Dependencies

Ensure you have Python 3 installed. Create and activate a virtual environment for the project, then install the required Python packages:

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

This will install `pandas`, `matplotlib`, `yfinance`, `QuantLib-Python`, `pandas_datareader`, and any other dependencies listed. **Note:** If QuantLib’s Python binding is not available via pip on your platform, refer to the [QuantLib Python installation instructions](https://quantlib-python-docs) for setup (QuantLib may require an additional install step on some systems).

### 3. Rust Toolchain and Build

Ensure you have Rust and Cargo installed (you can get Rust via [rustup](https://www.rust-lang.org/tools/install)). Then build the Rust backtester binary:

```bash
cargo build --release
```

This compiles the Rust project in release mode. After a successful build, the binary will be located at `target/release/rust_backtester_bin` (or `rust_backtester_bin.exe` on Windows). You can also run `cargo test` to run any unit tests (if included in the Rust codebase).

### 4. Prepare the Excel Event Data

Obtain the index addition events Excel file and place it in the appropriate location (by default the pipeline expects a file named **`Index Add Event Data.xlsx`** in a `data/` directory, but you can modify the path in the code or provide it as an argument). The Excel file should contain a table of index events with at least the following columns:

* **Ticker** – Stock symbol of the company added to the index.
* **Announcement Date** – The date when the index inclusion was announced (this is the date after market close or when the information became public).
* **Effective Date** (or **Trade Date**) – The date when the stock is actually added to the index (typically after market close of this day, the change takes effect; the strategy may use the opening of this day for event-day trades).
* **Index** – The index name (e.g., S\&P 500, S\&P 400, S\&P 600) to which the stock was added (useful for context or filtering).
* *Optional:* Any additional data columns (they will be ignored by the pipeline scripts if not needed). For instance, the dataset might include columns like “Addition/Deletion” (since only additions are considered here, all entries would be additions), or company name, etc.

Make sure the date columns are in a recognizable date format. If your file has a different structure or sheet name, you may need to adjust the code in `rant.py` (which uses pandas to read the Excel).

### 5. Configuration (Optional)

By default, the pipeline scripts may contain some configurable parameters (like strategy settings, holding periods, output file paths, etc.). Review the top of `rant.py` or a config file (if provided) to see if there are parameters you want to adjust. For example, you might find options for how many days to hold reversion trades or whether to generate charts. Adjust these as needed before running the pipeline.

## Usage Instructions

Once the environment is set up and the data file is in place, running the entire pipeline is straightforward. The process is managed by the **`pipeline.sh`** script.

1. **Activate the Python environment:** Before running, ensure your virtual environment is active:

   ```bash
   source venv/bin/activate
   ```

   (If you already installed dependencies in your global environment, this step is not needed, but using the venv is recommended to avoid conflicts.)

2. **Run the Pipeline Script:** Execute the bash script to launch the pipeline:

   ```bash
   ./pipeline.sh
   ```

   This will start the sequential process. The script will typically:

   * Run `rant.py` to perform the Python-side backtest calculations.
   * Invoke Cargo (or the built binary) to run the Rust backtester (`rust_backtester_bin`).
   * Run `performance.py` to calculate metrics.
   * Run `visualize.py` to generate charts.

   If `pipeline.sh` is not executable, give it execute permission first (`chmod +x pipeline.sh`). You can also run the steps manually if needed (e.g., `python rant.py`, then the Rust binary, etc.), but the script ensures the steps happen in the correct order with one command.

3. **Specify alternative data file (optional):** If your Excel file is named or located differently, you might pass it as an argument to `pipeline.sh` or set an environment variable. For example:

   ```bash
   ./pipeline.sh data/MyIndexEvents.xlsx
   ```

   (Check the script contents – it might accept a parameter for the file path. Otherwise, you can edit `pipeline.sh` or `rant.py` to point to the correct file.)

4. **Wait for completion:** The pipeline will output logs to the console for each step. Python steps will show progress for data download and any info or warnings from yfinance (downloading might take a few seconds per ticker). The Rust step will run quickly for the backtest computation. Once done, you should see summary outputs from the performance calculations.

5. **Review Outputs:** After successful run, look for:

   * **CSV Results:** For example, you might find `output/python_strategy_pnl.csv` and `output/rust_strategy_pnl.csv` (file names may vary) which contain detailed PnL results from Python and Rust respectively (per event or per day).
   * **Console Metrics:** The performance metrics (Sharpe, drawdown, etc.) may be printed to the console or saved to a text file. Check the terminal output for a summary of each strategy’s performance. If you want to save this, you can redirect output of the pipeline to a file.
   * **Charts:** In the `output/charts/` directory (or wherever specified in `visualize.py`), PNG image files will be created. These include equity curve plots and any comparison charts. You can open these to visually inspect how the strategies performed.

If any step fails or you encounter errors (for example, issues fetching data or parsing the Excel), the script will halt. In such cases, read the error message, adjust parameters (or ensure the data file is correctly formatted), and re-run. Common fixes include checking that all ticker symbols from the Excel are valid and still exist (some may have changed or delisted; the pipeline might skip or warn on missing data), or installing any missing system dependencies for QuantLib.

## Folder Structure

The repository is organized into directories separating data, outputs, and source code. Key files and folders include:

```
QuantStrategyPipeline/  
├── data/  
│   └── Index Add Event Data.xlsx        # Input data file with index addition events  
├── output/  
│   ├── python_results.csv              # Consolidated PnL results from Python (e.g., per event or daily)  
│   ├── rust_results.csv                # PnL results from Rust backtester  
│   └── charts/                         # Generated plots will be saved here  
│       ├── equity_curves.png           # Equity curves for strategies (Momentum, Reversion, Combined)  
│       ├── spy_performance.png         # SPY benchmark performance chart  
│       └── comparison_python_vs_rust.png   # Overlay of Python vs Rust results  
├── src/                                # Rust source code directory (for the rust_backtester_bin)  
│   ├── main.rs                         # Main Rust source file implementing backtest logic  
│   └── (other .rs files)               # Any additional Rust modules (if applicable)  
├── Cargo.toml                          # Rust project configuration (defines dependencies, project name, etc.)  
├── rant.py                             # Python script for data loading and strategy PnL computation  
├── performance.py                      # Python script for computing performance metrics from PnL results  
├── visualize.py                        # Python script for generating charts from the results  
├── pipeline.sh                         # Bash script to orchestrate the whole pipeline  
└── requirements.txt                    # List of Python dependencies for easy installation  
```

*(Note: The exact names of output files can be configured within the scripts. The above structure is an example; after running the pipeline you should see the actual output files as specified in the code.)*

## Component Details

Each major component in this pipeline serves a distinct purpose:

* **`pipeline.sh`:** A shell script that ties everything together. Running this script launches the full pipeline in sequence. It activates the Python virtual environment, ensures the Rust binary is built, and then calls the Python and Rust programs in order. Think of it as the automation glue – it saves you from manually running multiple commands. If you open this file, you’ll see the steps executed one after another (e.g., `python rant.py`, then `cargo run` or executing the binary, etc.). This script can be modified to change the order of steps or to add any pre/post-processing as needed.
* **`rant.py`:** The main Python strategy script (the name hints at perhaps "Rebalance Analysis Tool"). This script performs several critical tasks:

  1. **Data Loading:** Reads the Excel file containing index events into a pandas DataFrame.
  2. **Data Retrieval:** For each event (each stock and dates), it downloads the necessary historical price data using `yfinance`. Typically, it will download daily prices from a bit before the announcement date through a bit after the effective date to have all needed prices. It also retrieves benchmark data (like SPY prices) and interest rates from FRED.
  3. **Strategy Simulation:** Implements the logic for the momentum and reversion strategies. This involves determining entry and exit points for each trade according to the strategy definitions, calculating position sizes (the code might allocate equal capital per trade or something akin to using a portion of the \$5M portfolio per trade), and computing the profit or loss for each trade. The script handles multiple events possibly overlapping in time — depending on strategy, it could allow multiple concurrent positions (the portfolio might be split across events) or treat each event independently. It applies transaction costs and financing costs to each trade’s PnL.
  4. **Output Generation:** Aggregates all individual trade results into cumulative performance. It may create a time series of portfolio equity by applying each trade’s returns in chronological order. The script then outputs the results to CSV files (e.g., one for each strategy or one combined). These CSVs contain the PnL data that will be used by the Rust program and for performance analysis. For example, `rant.py` might output `momentum_pnl.csv` and `reversion_pnl.csv` (and possibly a combined portfolio PnL).
* **`performance.py`:** A Python script focused on computing performance metrics from the results of the backtest. It typically runs after both Python and Rust backtests are done (so that it can compare them if needed). This script reads in the PnL or returns data (from the CSVs or directly from `rant.py` if it shares data in memory) and calculates key metrics:

  * **Cumulative Return**: The total return of the strategy over the period.
  * **Annualized Return**: If the period spans more than a year, this metric annualizes the return.
  * **Volatility**: Standard deviation of returns (daily or per-event returns, properly annualized if needed).
  * **Sharpe Ratio**: Using a risk-free rate (could be based on Fed Funds average or 0 for simplicity), it computes Sharpe = (return - rf) / volatility.
  * **Max Drawdown**: Finds the largest drop from a peak in the equity curve.
  * **Calmar Ratio, Sortino Ratio, Win/Loss ratio**, etc.: Any other metric that might be relevant can be calculated here.

  It prints out or saves these metrics for each strategy (Momentum, Reversion, Combined) and perhaps for the benchmark. This helps in quickly assessing which strategy (if any) performed better or if the combined approach improved risk-adjusted returns.
* **`visualize.py`:** A Python script that reads the backtest results and generates visual charts. It likely uses `matplotlib` to create plots such as:

  * **Equity Curve per Strategy:** plotting the cumulative return of \$1 (or \$5M scaled to 1) over the sequence of events for the momentum strategy, reversion strategy, and their combined portfolio. This helps visualize performance event-by-event.
  * **Python vs Rust comparison:** plotting the equity curve derived from the Python backtest vs the Rust backtest to confirm they overlap (any divergence would indicate a discrepancy). This is usually done for the combined strategy or each strategy if needed.
  * **SPY Benchmark:** plotting the cumulative return of SPY over the same time frame as a baseline. This can be either in a separate chart or overlaid in a comparison chart. It provides context – e.g., if both strategies lost money while SPY gained, that tells an important story.

  The script will save these plots as image files (PNGs) in the `output/charts/` directory. It might also display them if run in an interactive environment (but when running via `pipeline.sh` in a non-GUI environment, it will just save to files).
* **Rust Backtester (`rust_backtester_bin`):** This is the compiled Rust program (source in the `src/` directory, primarily in `main.rs`). The Rust backtester is designed to perform the same calculations as the Python `rant.py` for verification and performance purposes. It likely:

  * Reads the input data (either directly from the Excel or more likely from the CSVs output by `rant.py` for consistency).
  * Implements the momentum and reversion strategies in Rust (applying the same rules for entry/exit and the same cost assumptions).
  * Outputs its results (cumulative PnL or per-event PnL) to a CSV file or console. The name `rust_backtester_bin` indicates it’s an independent executable; it might be invoked by `pipeline.sh` as `cargo run --release -- path/to/data.csv` or similar.

  Because Rust is much faster for heavy computations, this component could handle larger datasets or more complex simulations efficiently. In this project context, it serves as a cross-check to ensure that the strategy logic is correctly implemented (if both Python and Rust agree on results, we have high confidence in the correctness). If you plan to extend the strategies or run many simulations, the Rust engine can be invaluable for scaling up.

  *Note:* The Rust code likely uses standard crates for CSV parsing (`csv` crate) and possibly date handling (`chrono` crate) to deal with dates consistently. If the Rust program needed to fetch data itself, it could use an HTTP client crate to hit Yahoo’s API, but since we already have data from Python, the typical approach is to reuse that data.

## Sample Results and Charts

After running the pipeline, you can examine the performance of the strategies both numerically and visually. Below are examples of the kind of output charts the pipeline produces, along with brief explanations:

&#x20;*Figure: SPY Cumulative Returns (benchmark) from May 2022 through May 2025.* This chart shows the cumulative return of the S\&P 500 (using SPY as a proxy) over the same period during which the backtests were conducted. Starting in mid-2022, the SPY experienced periods of volatility but overall an upward trend, achieving a positive cumulative return by 2025. This benchmark performance provides context for the strategy results – a successful strategy might aim to outperform or decorrelate from this baseline. In our analysis, the SPY’s performance (roughly +20% to +30% over the period) serves as a yardstick to evaluate the momentum and reversion strategies.

&#x20;*Figure: Equity Curves by Strategy for Index Addition Events.* This chart plots the cumulative returns of each strategy across the sequence of index addition events (each event’s trade or series of trades impact the equity curve sequentially). The **Momentum strategy** (blue line) initially shows strong performance on early events (rising above a cumulative return of 1.1, or +10%), but later encounters volatility and a significant drawdown (dropping below 0.5, or -50% at one point). The **Reversion strategy** (orange line) exhibits a more gradual decline throughout – it underperforms in many events, leading to a steady erosion of equity to around 0.1 (an overall large loss). The **Combined strategy** (green line), which hypothetically allocates to both strategies (for example, splitting capital or taking all trades from both), starts near the average of the two and likewise declines when both strategies hit difficulties. By the end of the events, all strategies have struggled – an indication that these particular strategy implementations did not produce positive returns over the tested period. These equity curves are crucial for visualizing how each strategy behaved over time and for identifying where major gains or losses occurred (for instance, one can pinpoint around event 40-60 where the momentum strategy had its worst performance). Such insights could lead to further strategy refinement (or the conclusion that these approaches may not be effective as-is).

*(Additional charts:* The pipeline can also generate a comparison of the Python vs Rust cumulative PnL for the combined strategy, which ideally should overlap closely if both implementations are correct. Another chart can overlay the strategy’s equity curve against SPY’s curve over time to illustrate whether the strategy would have out- or under-performed the market. Refer to the `output/charts/` folder for all generated images.)\*

## License

This project is distributed under the **MIT License**. See the [LICENSE](LICENSE) file in the repository for the full license text.
