import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import time
import json # For JSON serialization

from alpha_vantage.timeseries import TimeSeries
import yfinance as yf
# import redis # Remove direct import of redis library

from ..core.config import settings
from ..core.redis_utils import redis_client # Import the shared client

# Remove local redis_client initialization, as it's now imported from redis_utils


_last_api_call_time_alpha_vantage: float = 0
ALPHA_VANTAGE_CALL_INTERVAL = 13 # Seconds (5 calls per minute free tier is 12s, add small buffer)


def _serialize_df(df: pd.DataFrame) -> bytes:
    """Serializes a Pandas DataFrame to JSON bytes for Redis storage."""
    # orient='split' is good for preserving index, columns, and data types where possible.
    # date_format='iso' ensures datetimes are stored in a standard ISO format.
    # default_handler=str handles any other types that JSON cannot serialize by default.
    return df.to_json(orient='split', date_format='iso', default_handler=str).encode('utf-8')

def _deserialize_df(json_bytes: Optional[bytes]) -> Optional[pd.DataFrame]:
    """Deserializes JSON bytes from Redis back into a Pandas DataFrame."""
    if not json_bytes:
        return None
    try:
        json_str = json_bytes.decode('utf-8')
        df = pd.read_json(json_str, orient='split')
        # Ensure the index is converted to DatetimeIndex.
        # pd.read_json with orient='split' should handle index dtype correctly if it was DatetimeIndex.
        # If not, or to be absolutely sure:
        if not isinstance(df.index, pd.DatetimeIndex):
             df.index = pd.to_datetime(df.index, errors='coerce')

        # Ensure 'price' and 'volume' columns are numeric, coercing errors.
        for col in ['price', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        print(f"Error deserializing DataFrame from Redis: {e}")
        return None


def _fetch_with_alpha_vantage(ticker: str, api_key: str) -> Optional[pd.DataFrame]:
    global _last_api_call_time_alpha_vantage

    av_ticker = ticker
    if ticker.endswith(".SA"):
        av_ticker = ticker[:-3] + ".SAO"

    # Cache key specific to Alpha Vantage and the full daily adjusted data request
    cache_key = f"marketdata:av:{av_ticker}:daily_adjusted_full"

    if redis_client:
        # Try to fetch from Redis cache first
        cached_data_bytes = redis_client.get(cache_key)
        if cached_data_bytes:
            print(f"Cache hit (Redis) for Alpha Vantage: {av_ticker}")
            df = _deserialize_df(cached_data_bytes)
            if df is not None: return df.copy()
            else: print(f"Failed to deserialize cached AV data for {av_ticker}, will re-fetch.")

    # Rate limiting for Alpha Vantage API calls
    elapsed_time = time.time() - _last_api_call_time_alpha_vantage
    if elapsed_time < ALPHA_VANTAGE_CALL_INTERVAL:
        wait_time = ALPHA_VANTAGE_CALL_INTERVAL - elapsed_time
        print(f"Alpha Vantage: Rate limiting, sleeping for {wait_time:.2f} seconds for {av_ticker}.")
        time.sleep(wait_time)

    ts = TimeSeries(key=api_key, output_format='pandas')
    _last_api_call_time_alpha_vantage = time.time()

    try:
        print(f"Alpha Vantage: Fetching API for {av_ticker} (original: {ticker})")
        data, meta_data = ts.get_daily_adjusted(symbol=av_ticker, outputsize='full')

        if data.empty:
            print(f"Alpha Vantage: No data returned for {av_ticker}")
            return None

        data = data.rename(columns={'5. adjusted close': 'price', '6. volume': 'volume'})
        cols_to_keep = [col for col in ['price', 'volume'] if col in data.columns]
        if not cols_to_keep:
            print(f"Alpha Vantage: Relevant columns not found for {av_ticker}")
            return None

        data = data[cols_to_keep].sort_index(ascending=True)
        data.index = pd.to_datetime(data.index)

        if redis_client and not data.empty:
            # Serialize and store fetched data in Redis cache
            serialized_df = _serialize_df(data)
            redis_client.setex(cache_key, settings.MARKET_DATA_CACHE_TTL_SECONDS, serialized_df)
            print(f"Cached Alpha Vantage data for {av_ticker} in Redis (TTL: {settings.MARKET_DATA_CACHE_TTL_SECONDS}s).")
        return data.copy()
    except Exception as e:
        print(f"Alpha Vantage API error for {av_ticker}: {e}")
        if "call frequency" in str(e).lower() or "premium" in str(e).lower():
             print("Alpha Vantage API rate limit hit or premium feature.")
        return None


def _fetch_with_yfinance(ticker: str) -> Optional[pd.DataFrame]:
    cache_key = f"marketdata:yf:{ticker}:history_10y"

    if redis_client:
        # Try to fetch from Redis cache first
        cached_data_bytes = redis_client.get(cache_key)
        if cached_data_bytes:
            print(f"Cache hit (Redis) for yfinance: {ticker}")
            df = _deserialize_df(cached_data_bytes)
            if df is not None: return df.copy()
            else: print(f"Failed to deserialize cached yfinance data for {ticker}, will re-fetch.")
    try:
        print(f"yfinance: Fetching API for {ticker}")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="10y", auto_adjust=True, progress=False)

        if hist.empty:
            print(f"yfinance: No data for {ticker}")
            return None

        hist = hist.rename(columns={'Close': 'price', 'Volume': 'volume'})
        cols_to_keep = [col for col in ['price', 'volume'] if col in hist.columns]
        if not cols_to_keep:
            print(f"yfinance: Relevant columns not found for {ticker}")
            return None

        hist = hist[cols_to_keep]
        hist.index = pd.to_datetime(hist.index)

        if redis_client and not hist.empty:
            # Serialize and store fetched data in Redis cache
            serialized_df = _serialize_df(hist)
            redis_client.setex(cache_key, settings.MARKET_DATA_CACHE_TTL_SECONDS, serialized_df)
            print(f"Cached yfinance data for {ticker} in Redis (TTL: {settings.MARKET_DATA_CACHE_TTL_SECONDS}s).")
        return hist.copy()
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None


def fetch_historical_data(ticker: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetches historical price and volume data for a given ticker, utilizing Redis caching.

    This function orchestrates data fetching by first trying Alpha Vantage (if an API key
    is available in settings) and then falling back to yfinance if the primary source fails
    or returns no data. Both underlying fetch methods (`_fetch_with_alpha_vantage` and
    `_fetch_with_yfinance`) implement Redis caching for the raw data they retrieve.

    The caching strategy involves:
    - Storing the full historical data chunk from the provider (e.g., 'full' series from AV, '10y' from yf)
      under a provider-specific key (e.g., `marketdata:av:TICKER.SAO:daily_adjusted_full` or
      `marketdata:yf:TICKER.SA:history_10y`).
    - DataFrames are serialized to JSON strings then to bytes for Redis storage.
    - A Time-To-Live (TTL) is applied, configured by `settings.MARKET_DATA_CACHE_TTL_SECONDS`.
    - If `force_refresh` is True, relevant cache keys for the ticker are deleted from Redis
      before attempting to fetch from external APIs.
    - If Redis is unavailable, caching is skipped, and data is fetched directly.

    After potentially retrieving from cache or fetching and caching, this function performs
    date slicing based on `start_date_str` and `end_date_str` on a *copy* of the data.

    Args:
        ticker: The stock ticker symbol (e.g., "PETR4.SA").
        start_date_str: Optional start date in "YYYY-MM-DD" format. If None, data from the
                        earliest point in the cached/fetched series is considered.
        end_date_str: Optional end date in "YYYY-MM-DD" format. If None, data up to the
                      latest point in the cached/fetched series is considered.
        force_refresh: If True, forces a fresh fetch from external APIs by attempting to
                       delete existing cache entries for the ticker first.

    Returns:
        A pandas DataFrame with 'price' (adjusted close) and 'volume' columns, indexed by
        timezone-naive datetime. Returns an empty DataFrame with these columns if data
        cannot be fetched or if no data exists for the specified period after slicing.
    """
    print(f"Fetching historical data for ticker: {ticker} (Force Refresh: {force_refresh})")

    # Construct cache keys based on how _fetch_... methods would create them
    av_ticker_formatted = ticker[:-3] + ".SAO" if ticker.endswith(".SA") else ticker
    av_cache_key = f"marketdata:av:{av_ticker_formatted}:daily_adjusted_full"
    yf_cache_key = f"marketdata:yf:{ticker}:history_10y"

    if force_refresh and redis_client:
        print(f"Force refresh: Deleting cache for {ticker} (AV: {av_cache_key}, YF: {yf_cache_key})")
        # Delete both potential cache keys, as we don't know which one might exist or be used.
        keys_to_delete = [av_cache_key, yf_cache_key]
        # Filter out None or empty strings if any key construction results in that (should not happen here)
        valid_keys_to_delete = [key for key in keys_to_delete if key]
        if valid_keys_to_delete:
            redis_client.delete(*valid_keys_to_delete)


    raw_df: Optional[pd.DataFrame] = None

    if settings.ALPHA_VANTAGE_API_KEY:
        raw_df = _fetch_with_alpha_vantage(ticker, settings.ALPHA_VANTAGE_API_KEY)

    if raw_df is None or raw_df.empty:
        if settings.ALPHA_VANTAGE_API_KEY and raw_df is not None: # AV tried, returned empty
             print(f"Alpha Vantage returned no data for {ticker}. Falling back to yfinance.")
        elif not settings.ALPHA_VANTAGE_API_KEY: # AV not tried
             print(f"No Alpha Vantage API key. Using yfinance for {ticker}.")
        else: # AV tried and failed (raw_df is None)
             print(f"Alpha Vantage fetch failed for {ticker}. Falling back to yfinance.")
        raw_df = _fetch_with_yfinance(ticker)

    if raw_df is None or raw_df.empty:
        print(f"Could not fetch data for {ticker} from any source.")
        return pd.DataFrame(columns=['price', 'volume'], index=pd.to_datetime([]))

    df_to_slice = raw_df.copy() # Work with a copy for slicing
    if df_to_slice.index.tz is not None: # Ensure index is timezone-naive for consistent slicing
        df_to_slice.index = df_to_slice.index.tz_localize(None)

    result_df = df_to_slice
    if start_date_str:
        s_date = pd.to_datetime(start_date_str).replace(tzinfo=None)
        result_df = result_df[result_df.index >= s_date]
    if end_date_str:
        e_date = pd.to_datetime(end_date_str).replace(tzinfo=None)
        result_df = result_df[result_df.index <= e_date]

    return result_df.copy()


def get_asset_data_sample(ticker: str, n_points: int = 252) -> pd.DataFrame:
    # Fetch enough historical data then take tail.
    # force_refresh=False by default, so it uses cache if available for the underlying fetch.
    df = fetch_historical_data(ticker, end_date_str=datetime.now().strftime('%Y-%m-%d'))
    if df.empty: return pd.DataFrame(columns=['price', 'volume'], index=pd.to_datetime([]))
    return df.tail(n_points)

def get_available_assets() -> list[str]:
    common_b3_tickers = [
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
        "WEGE3.SA", "MGLU3.SA", "LREN3.SA", "B3SA3.SA", "SUZB3.SA", "BOVA11.SA"
    ]
    return common_b3_tickers

def fetch_asset_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = fetch_historical_data(ticker, start_date_str=start_date, end_date_str=end_date)
    if 'price' in df.columns: return df[['price']]
    return pd.DataFrame(columns=['price'], index=pd.to_datetime([]))
```
