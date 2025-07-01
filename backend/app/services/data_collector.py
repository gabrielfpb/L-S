import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import time

from alpha_vantage.timeseries import TimeSeries
import yfinance as yf

from ..core.config import settings

# In-memory cache for API call results for the current session
_api_call_cache: Dict[str, pd.DataFrame] = {}
_last_api_call_time_alpha_vantage: float = 0
ALPHA_VANTAGE_CALL_INTERVAL = 13 # Seconds (5 calls per minute free tier is 12s, add small buffer)


def _fetch_with_alpha_vantage(ticker: str, api_key: str) -> Optional[pd.DataFrame]:
    global _last_api_call_time_alpha_vantage

    elapsed_time = time.time() - _last_api_call_time_alpha_vantage
    if elapsed_time < ALPHA_VANTAGE_CALL_INTERVAL:
        wait_time = ALPHA_VANTAGE_CALL_INTERVAL - elapsed_time
        print(f"Alpha Vantage: Rate limiting, sleeping for {wait_time:.2f} seconds.")
        time.sleep(wait_time)

    ts = TimeSeries(key=api_key, output_format='pandas')
    _last_api_call_time_alpha_vantage = time.time()

    try:
        # Alpha Vantage ticker for B3 might be like "PETR4.SAO"
        av_ticker = ticker
        if ticker.endswith(".SA"): # Common yfinance B3 suffix
            av_ticker = ticker[:-3] + ".SAO"

        print(f"Alpha Vantage: Fetching daily adjusted for {av_ticker} (original: {ticker})")
        # Use get_daily_adjusted for adjusted prices which are generally preferred
        data, meta_data = ts.get_daily_adjusted(symbol=av_ticker, outputsize='full')

        if data.empty:
            print(f"Alpha Vantage: No data returned for {av_ticker}")
            return None

        # Rename columns to a standard format ('price', 'volume')
        # Alpha Vantage daily adjusted columns:
        # '1. open', '2. high', '3. low', '4. close', '5. adjusted close', '6. volume', '7. dividend amount', '8. split coefficient'
        data = data.rename(columns={'5. adjusted close': 'price', '6. volume': 'volume'})

        cols_to_keep = []
        if 'price' in data.columns: cols_to_keep.append('price')
        if 'volume' in data.columns: cols_to_keep.append('volume')

        if not cols_to_keep:
            print(f"Alpha Vantage: Relevant columns ('price', 'volume') not found for {av_ticker}")
            return None

        data = data[cols_to_keep].sort_index(ascending=True)
        data.index = pd.to_datetime(data.index) # Ensure index is DatetimeIndex
        return data
    except Exception as e:
        print(f"Alpha Vantage API error for {av_ticker} (original: {ticker}): {e}")
        if "call frequency" in str(e).lower() or "premium" in str(e).lower():
             print("Alpha Vantage API rate limit likely hit or feature requires premium.")
        return None


def _fetch_with_yfinance(ticker: str) -> Optional[pd.DataFrame]:
    # yfinance usually expects ".SA" for B3 tickers, e.g., "PETR4.SA"
    yf_ticker = ticker
    # yfinance handles most international tickers correctly if they are standard.
    # No complex suffix adjustment needed here usually, unlike Alpha Vantage sometimes.

    try:
        print(f"yfinance: Fetching history for {yf_ticker}")
        stock = yf.Ticker(yf_ticker)
        # Fetching 10 years of data. auto_adjust=True handles splits/dividends for 'Close' price.
        hist = stock.history(period="10y", auto_adjust=True, progress=False)

        if hist.empty:
            print(f"yfinance: No data for {yf_ticker}")
            return None

        # yfinance with auto_adjust=True usually returns 'Close' and 'Volume'.
        # 'Open', 'High', 'Low' are also there. 'Dividends', 'Stock Splits'.
        hist = hist.rename(columns={'Close': 'price', 'Volume': 'volume'})

        cols_to_keep = []
        if 'price' in hist.columns: cols_to_keep.append('price')
        if 'volume' in hist.columns: cols_to_keep.append('volume')

        if not cols_to_keep:
            print(f"yfinance: Relevant columns ('price', 'volume') not found for {yf_ticker}")
            return None

        hist = hist[cols_to_keep]
        hist.index = pd.to_datetime(hist.index) # Ensure index is DatetimeIndex
        return hist
    except Exception as e:
        print(f"yfinance error for {yf_ticker}: {e}")
        return None


def fetch_historical_data(ticker: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetches historical price and volume data for a given ticker.
    Uses Alpha Vantage if API key is available, otherwise falls back to yfinance.
    Fetches historical price and volume data for a given ticker.

    Prioritizes Alpha Vantage if an API key is configured and available,
    otherwise falls back to yfinance. Implements basic rate limiting for Alpha Vantage
    and in-memory caching for API call results within the current session to minimize
    redundant external API calls.

    Args:
        ticker: The stock ticker symbol (e.g., "PETR4.SA"). Format may need adjustment
                based on the data provider (e.g., Alpha Vantage might prefer "PETR4.SAO" for B3).
        start_date_str: Optional start date in "YYYY-MM-DD" format. If None, fetches data from earliest available.
        end_date_str: Optional end date in "YYYY-MM-DD" format. If None, fetches data up to latest available.
        force_refresh: If True, bypasses the in-memory cache and fetches fresh data from the APIs.

    Returns:
        A pandas DataFrame with 'price' (adjusted close) and 'volume' columns, indexed by datetime.
        The datetime index is timezone-naive.
        Returns an empty DataFrame with these columns if data cannot be fetched or no data exists for the period.
    """
    cache_key = f"{ticker}_{start_date_str}_{end_date_str}" # Simple cache key
    if not force_refresh and cache_key in _api_call_cache:
        print(f"Returning cached data for {cache_key}")
        return _api_call_cache[cache_key].copy()

    print(f"Fetching real market data for ticker: {ticker}...")
    raw_df: Optional[pd.DataFrame] = None

    if settings.ALPHA_VANTAGE_API_KEY:
        raw_df = _fetch_with_alpha_vantage(ticker, settings.ALPHA_VANTAGE_API_KEY)

    if raw_df is None or raw_df.empty:
        if settings.ALPHA_VANTAGE_API_KEY and raw_df is not None: # AV was tried but returned empty
             print(f"Alpha Vantage returned no data for {ticker}. Falling back to yfinance.")
        elif not settings.ALPHA_VANTAGE_API_KEY:
             print(f"No Alpha Vantage API key provided. Using yfinance for {ticker}.")
        else: # AV was tried and failed (raw_df is None)
             print(f"Alpha Vantage fetch failed for {ticker}. Falling back to yfinance.")
        raw_df = _fetch_with_yfinance(ticker)

    if raw_df is None or raw_df.empty:
        print(f"Could not fetch data for {ticker} from any source.")
        # Cache empty dataframe to avoid retrying failed tickers repeatedly in same session
        _api_call_cache[cache_key] = pd.DataFrame(columns=['price', 'volume'])
        return _api_call_cache[cache_key].copy()

    # Ensure index is timezone-naive for consistency before slicing
    if raw_df.index.tz is not None:
        raw_df.index = raw_df.index.tz_localize(None)

    result_df = raw_df.copy()
    if start_date_str:
        s_date = pd.to_datetime(start_date_str).replace(tzinfo=None)
        result_df = result_df[result_df.index >= s_date]
    if end_date_str:
        e_date = pd.to_datetime(end_date_str).replace(tzinfo=None)
        result_df = result_df[result_df.index <= e_date]

    _api_call_cache[cache_key] = result_df.copy() # Cache the (possibly sliced) dataframe
    return result_df


def get_asset_data_sample(ticker: str, n_points: int = 252) -> pd.DataFrame:
    """
    Fetches the last N data points (adjusted close 'price' and 'volume') for a given asset ticker.

    This function utilizes `fetch_historical_data` to get a broader range of data first,
    then extracts the tail end. This is generally more efficient than trying to calculate
    an exact start date for N points due to holidays and non-trading days.

    Args:
        ticker: The stock ticker symbol.
        n_points: The number of recent data points to retrieve. Defaults to 252 (approx 1 year).

    Returns:
        A pandas DataFrame with 'price' and 'volume' columns for the last N points,
        indexed by datetime. Returns an empty DataFrame if no data is available.
    """
    # Fetch a larger chunk of data and then take the tail.
    # Calculate a rough start date to ensure enough data, assuming ~252 trading days a year.
    # Add buffer for non-trading days.
    years_to_fetch = (n_points / 252.0) + 0.5 # Add half year buffer
    start_date_approx = (datetime.now() - timedelta(days=years_to_fetch * 365.25)).strftime('%Y-%m-%d')

    df = fetch_historical_data(ticker, start_date_str=start_date_approx, end_date_str=datetime.now().strftime('%Y-%m-%d'))

    if df.empty:
        return pd.DataFrame(columns=['price', 'volume'])

    return df.tail(n_points)

def get_available_assets() -> list[str]:
    """
    Returns a predefined list of common B3 tickers, primarily formatted for yfinance.
    This list can be expanded or made dynamic in a real application.
    """
    common_b3_tickers = [
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
        "WEGE3.SA", "MGLU3.SA", "LREN3.SA", "B3SA3.SA", "SUZB3.SA",
        "RENT3.SA", "PRIO3.SA", "RDOR3.SA", "EQTL3.SA", "GGBR4.SA",
        "BOVA11.SA" # BOVESPA Index ETF
    ]
    # Example US tickers (yfinance format)
    # common_us_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    print(f"Returning predefined list of B3 tickers (primarily yfinance format).")
    return common_b3_tickers

def fetch_asset_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Public function to fetch historical *price* data for a specific ticker and date range.
    This is typically the main function that API routes related to simple price history should call.
    It leverages `fetch_historical_data` and then ensures only the 'price' column is returned.

    Args:
        ticker: The stock ticker symbol.
        start_date: Start date string in "YYYY-MM-DD" format.
        end_date: End date string in "YYYY-MM-DD" format.

    Returns:
        A pandas DataFrame with a single 'price' column, indexed by datetime.
        Returns an empty DataFrame with a 'price' column if no data is found.
    """
    df = fetch_historical_data(ticker, start_date_str=start_date, end_date_str=end_date)
    if 'price' in df.columns:
        return df[['price']]
    return pd.DataFrame(columns=['price'])
```
