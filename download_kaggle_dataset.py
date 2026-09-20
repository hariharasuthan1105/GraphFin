"""
Utility script to download the Time Series of Transactions - Money Laundering dataset from Kaggle.
Dataset: haroldg/time-series-of-transactions-money-laundering
"""
import sys
from pathlib import Path


def download_dataset() -> str:
    """Download the money laundering time series dataset via kagglehub."""
    try:
        import kagglehub
    except ImportError:
        print("kagglehub is not installed. Please run: pip install kagglehub", file=sys.stderr)
        sys.exit(1)

    print("Downloading 'haroldg/time-series-of-transactions-money-laundering' via kagglehub...")
    path = kagglehub.dataset_download(
        "haroldg/time-series-of-transactions-money-laundering"
    )
    print("Path to dataset files:", path)
    return path


if __name__ == "__main__":
    download_dataset()
