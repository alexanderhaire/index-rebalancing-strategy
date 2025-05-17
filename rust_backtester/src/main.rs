use std::{
    error::Error,
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

use csv;
use serde::Deserialize;

#[derive(Deserialize)]
struct ReplayRow {
    portfolio: f64,
}

#[derive(Deserialize)]
struct RustRow {
    #[serde(rename = "mom_score")]
    mom_score: f64,
    #[serde(rename = "rev_score")]
    rev_score: f64,
    // When you’re ready to do the “real” backtest,
    // you can also deserialize:
    // Announced: String,
    // TradeDate: String,
    // Ticker: String,
    // price: f64,
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 5 || args[1] != "--input" || args[3] != "--output" {
        eprintln!("Usage: {} --input <in.csv> --output <out.csv>", args[0]);
        std::process::exit(1);
    }
    let input_path = &args[2];
    let output_path = &args[4];

    // 1) Open the input CSV
    let input_file = File::open(Path::new(input_path))?;
    let mut rdr = csv::Reader::from_reader(BufReader::new(input_file));

    // 2) Prepare the output writer
    let output_file = File::create(Path::new(output_path))?;
    let mut wtr = csv::Writer::from_writer(BufWriter::new(output_file));

    // 3) Write header
    wtr.write_record(&["pnl"])?;

    // 4) Inspect headers to choose mode
    let headers = rdr.headers()?;
    if headers.iter().any(|h| h == "portfolio") {
        // === REPLAY MODE ===
        for result in rdr.deserialize() {
            let row: ReplayRow = result?;
            wtr.serialize((row.portfolio,))?;
        }
    } else {
        // === REAL P&L MODE (stub) ===
        for result in rdr.deserialize() {
            let row: RustRow = result?;
            // <<< your P&L logic here >>>
            let pnl = row.mom_score + row.rev_score;
            wtr.serialize((pnl,))?;
        }
    }

    // 5) Flush and finish
    wtr.flush()?;
    Ok(())
}
