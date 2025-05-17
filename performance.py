import pandas as pd

def performance_metrics(series: pd.Series) -> dict:
    # simple example metrics
    return {
        "total_return": float(series.iloc[-1]),
        "mean_return":  float(series.mean()),
        "std_dev":      float(series.std()),
    }

if __name__ == "__main__":
    import sys
    df = pd.read_csv(sys.argv[1])
    print(performance_metrics(df.iloc[:,0]))
