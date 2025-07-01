import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np # Ensure numpy is imported for fixtures if needed

from app.services.data_collector import (
    fetch_historical_data,
    _fetch_with_alpha_vantage,
    _fetch_with_yfinance,
    get_asset_data_sample,
    _serialize_df # Import for test setup convenience
)
from app.core.config import settings

# --- Fixtures for mock data and API responses ---

@pytest.fixture
def mock_alpha_vantage_success_df():
    return pd.DataFrame({
        'price': [100.0, 101.0, 102.0],
        'volume': [1000, 1100, 1200]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))

@pytest.fixture
def mock_yfinance_success_df():
    return pd.DataFrame({
        'price': [90.0, 91.0, 92.0],
        'volume': [2000, 2100, 2200]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))

@pytest.fixture
def mock_alpha_vantage_api(monkeypatch, mock_alpha_vantage_success_df):
    mock_ts_instance = MagicMock()
    mock_ts_instance.get_daily_adjusted.return_value = (mock_alpha_vantage_success_df, {"2. Symbol": "TEST.SAO"})
    mock_timeseries = MagicMock(return_value=mock_ts_instance)
    monkeypatch.setattr("app.services.data_collector.TimeSeries", mock_timeseries)
    return mock_timeseries

@pytest.fixture
def mock_yfinance_api(monkeypatch, mock_yfinance_success_df):
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = mock_yfinance_success_df
    mock_yf_ticker = MagicMock(return_value=mock_ticker_instance)
    monkeypatch.setattr("app.services.data_collector.yf.Ticker", mock_yf_ticker)
    return mock_yf_ticker

# --- Tests for Redis Caching ---

@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_cache_hit_alpha_vantage(
    mock_redis, mock_alpha_vantage_api, mock_alpha_vantage_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV_HIT")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)

    serialized_df = _serialize_df(mock_alpha_vantage_success_df)
    mock_redis.get.return_value = serialized_df

    ticker = "HIT.SA"
    expected_av_cache_key = f"marketdata:av:HIT.SAO:daily_adjusted_full"

    df = fetch_historical_data(ticker, "2023-01-01", "2023-01-03")

    mock_redis.get.assert_called_once_with(expected_av_cache_key)
    # Access the mock object created by the @patch decorator for TimeSeries inside the fixture
    mock_alpha_vantage_api.return_value.get_daily_adjusted.assert_not_called()
    assert not df.empty
    assert df['price'].iloc[0] == 100.0


@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_cache_miss_then_store_alpha_vantage(
    mock_redis, mock_alpha_vantage_api, mock_alpha_vantage_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV_MISS")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)
    mock_redis.get.return_value = None

    ticker = "MISS.SA"
    expected_av_cache_key = f"marketdata:av:MISS.SAO:daily_adjusted_full"
    expected_serialized_df = _serialize_df(mock_alpha_vantage_success_df)

    df = fetch_historical_data(ticker, "2023-01-01", "2023-01-03")

    mock_redis.get.assert_called_once_with(expected_av_cache_key)
    mock_alpha_vantage_api.return_value.get_daily_adjusted.assert_called_once()
    mock_redis.setex.assert_called_once_with(
        expected_av_cache_key,
        settings.MARKET_DATA_CACHE_TTL_SECONDS,
        expected_serialized_df
    )
    assert not df.empty
    assert df['price'].iloc[0] == 100.0


@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_cache_hit_yfinance(
    mock_redis, mock_yfinance_api, mock_yfinance_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", None)

    serialized_df = _serialize_df(mock_yfinance_success_df)
    mock_redis.get.return_value = serialized_df

    ticker = "YFHIT.SA"
    expected_yf_cache_key = f"marketdata:yf:{ticker}:history_10y"

    df = fetch_historical_data(ticker, "2023-01-01", "2023-01-03")

    mock_redis.get.assert_called_once_with(expected_yf_cache_key)
    mock_yfinance_api.return_value.history.assert_not_called()
    assert not df.empty
    assert df['price'].iloc[0] == 90.0


@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_cache_miss_then_store_yfinance(
    mock_redis, mock_yfinance_api, mock_yfinance_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", None)
    mock_redis.get.return_value = None

    ticker = "YFMISS.SA"
    expected_yf_cache_key = f"marketdata:yf:{ticker}:history_10y"
    expected_serialized_df = _serialize_df(mock_yfinance_success_df)

    df = fetch_historical_data(ticker, "2023-01-01", "2023-01-03")

    mock_redis.get.assert_called_once_with(expected_yf_cache_key)
    mock_yfinance_api.return_value.history.assert_called_once()
    mock_redis.setex.assert_called_once_with(
        expected_yf_cache_key,
        settings.MARKET_DATA_CACHE_TTL_SECONDS,
        expected_serialized_df
    )
    assert not df.empty
    assert df['price'].iloc[0] == 90.0


@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_force_refresh_deletes_cache_and_fetches(
    mock_redis, mock_alpha_vantage_api, mock_alpha_vantage_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV_FORCE")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)

    # _fetch_with_alpha_vantage will try to get from cache first.
    # If force_refresh in fetch_historical_data works, it deletes before _fetch_with_alpha_vantage is called.
    # So, redis.get inside _fetch_with_alpha_vantage should return None.
    mock_redis.get.return_value = None

    ticker = "FORCE.SA"
    expected_av_cache_key = f"marketdata:av:FORCE.SAO:daily_adjusted_full"
    expected_yf_cache_key = f"marketdata:yf:FORCE.SA:history_10y" # Fallback key also deleted

    fetch_historical_data(ticker, "2023-01-01", "2023-01-03", force_refresh=True)

    # Check delete was called for potential keys
    mock_redis.delete.assert_any_call(expected_av_cache_key)
    mock_redis.delete.assert_any_call(expected_yf_cache_key)

    mock_alpha_vantage_api.return_value.get_daily_adjusted.assert_called_once()
    mock_redis.setex.assert_called_once()


@patch('app.services.data_collector.redis_client', None)
def test_fetch_historical_data_redis_unavailable_falls_back_gracefully(
    mock_alpha_vantage_api, mock_yfinance_api, mock_alpha_vantage_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_NO_REDIS")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)

    df = fetch_historical_data("NOREDIS.SA", "2023-01-01", "2023-01-03")

    mock_alpha_vantage_api.return_value.get_daily_adjusted.assert_called_once()
    assert not df.empty
    assert df['price'].iloc[0] == 100.0


@patch('app.services.data_collector.redis_client')
def test_fetch_historical_data_uses_alpha_vantage_with_key_and_redis(
    mock_redis, mock_alpha_vantage_api, mock_alpha_vantage_success_df, monkeypatch
):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)
    mock_redis.get.return_value = None # Cache miss

    df = fetch_historical_data("DUMMY.SA")
    assert df is not None
    assert not df.empty
    assert df['price'].iloc[0] == 100.0
    mock_alpha_vantage_api.return_value.get_daily_adjusted.assert_called_with(symbol="DUMMY.SAO", outputsize='full')
    mock_redis.setex.assert_called_once()
```
