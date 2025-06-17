import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Simulated data store (in a real app, this would be an external API or database)
SIMULATED_ASSET_DB = {
    "PETR4.SA": pd.DataFrame({
        'timestamp': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(100_0, 0, -1)]),
        'price': np.random.normal(loc=30, scale=2, size=100_0) + np.arange(100_0) * 0.01
    }).set_index('timestamp'),
    "VALE3.SA": pd.DataFrame({
        'timestamp': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(100_0, 0, -1)]),
        'price': np.random.normal(loc=70, scale=5, size=100_0) - np.arange(100_0) * 0.005
    }).set_index('timestamp'),
    "ITUB4.SA": pd.DataFrame({
        'timestamp': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(100_0, 0, -1)]),
        'price': np.random.normal(loc=25, scale=1.5, size=100_0) + np.sin(np.arange(100_0) / 50) * 0.5
    }).set_index('timestamp'),
    "BBDC4.SA": pd.DataFrame({
        'timestamp': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(100_0, 0, -1)]),
        'price': np.random.normal(loc=20, scale=1.0, size=100_0) + np.sin(np.arange(100_0) / 60) * 0.3
    }).set_index('timestamp'),
}

def fetch_asset_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical price data for a given asset ticker between start_date and end_date.
    In this simulated version, it slices the data from SIMULATED_ASSET_DB.
    """
    print(f"Fetching data for {ticker} from {start_date} to {end_date}...")
    if ticker not in SIMULATED_ASSET_DB:
        raise ValueError(f"Asset data for ticker {ticker} not found.")

    try:
        s_date = pd.to_datetime(start_date)
        e_date = pd.to_datetime(end_date)
    except ValueError:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

    if s_date > e_date:
        raise ValueError("Start date cannot be after end date.")

    asset_df = SIMULATED_ASSET_DB[ticker]
    # Ensure the index is sorted for proper slicing
    asset_df = asset_df.sort_index()

    # Slice the data, handling cases where dates might be out of bounds
    data_slice = asset_df[(asset_df.index >= s_date) & (asset_df.index <= e_date)]

    if data_slice.empty:
        # This could mean requested range is outside available data, or no data for the period
        print(f"No data found for {ticker} between {start_date} and {end_date}.")
        # Return an empty DataFrame with the expected column to avoid downstream errors
        return pd.DataFrame(columns=['price'])

    return data_slice[['price']] # Return only the price column

def get_available_assets() -> list[str]:
    """
    Returns a list of available asset tickers.
    """
    print("Fetching list of available assets...")
    return list(SIMULATED_ASSET_DB.keys())

# Example: Add a function to get a small sample for testing
def get_asset_data_sample(ticker: str, n_points: int = 252) -> pd.DataFrame: # Approx 1 year of trading days
    """
    Fetches the last N data points for an asset.
    """
    if ticker not in SIMULATED_ASSET_DB:
        raise ValueError(f"Asset data for ticker {ticker} not found.")

    asset_df = SIMULATED_ASSET_DB[ticker].sort_index()
    return asset_df[['price']].tail(n_points)
