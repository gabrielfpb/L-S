import pytest
import pandas as pd
from unittest.mock import patch, MagicMock # For mocking external API calls
from datetime import datetime

from app.services.data_collector import (
    fetch_historical_data,
    _fetch_with_alpha_vantage,
    _fetch_with_yfinance,
    get_asset_data_sample
)
from app.core.config import settings # To temporarily set API key for testing specific path

@pytest.fixture
def mock_alpha_vantage_success(monkeypatch):
    mock_ts_instance = MagicMock()
    # Ensure datetime index for mock data
    mock_data_index = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    mock_data = pd.DataFrame({
        '5. adjusted close': [100.0, 101.0, 102.0],
        '6. volume': [1000, 1100, 1200]
    }, index=mock_data_index)
    mock_ts_instance.get_daily_adjusted.return_value = (mock_data, {"2. Symbol": "TEST.SAO"})

    mock_timeseries = MagicMock(return_value=mock_ts_instance)
    monkeypatch.setattr("app.services.data_collector.TimeSeries", mock_timeseries)
    return mock_timeseries

@pytest.fixture
def mock_yfinance_success(monkeypatch):
    mock_ticker_instance = MagicMock()
    mock_data_index = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    mock_data = pd.DataFrame({
        'Close': [90.0, 91.0, 92.0],
        'Volume': [2000, 2100, 2200]
    }, index=mock_data_index) # Ensure datetime index
    mock_ticker_instance.history.return_value = mock_data

    mock_yf_ticker = MagicMock(return_value=mock_ticker_instance)
    monkeypatch.setattr("app.services.data_collector.yf.Ticker", mock_yf_ticker)
    return mock_yf_ticker

def test_fetch_with_alpha_vantage_success(mock_alpha_vantage_success, monkeypatch):
    # Temporarily set API key for this test
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY")
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)

    df = _fetch_with_alpha_vantage("TEST.SA", "TESTKEY")
    assert df is not None
    assert not df.empty
    assert 'price' in df.columns
    assert df['price'].iloc[0] == 100.0
    mock_alpha_vantage_success.assert_called_once_with(key="TESTKEY", output_format='pandas')
    mock_alpha_vantage_success.return_value.get_daily_adjusted.assert_called_once_with(symbol="TEST.SAO", outputsize='full')

def test_fetch_with_yfinance_success(mock_yfinance_success):
    df = _fetch_with_yfinance("TEST.SA")
    assert df is not None
    assert not df.empty
    assert 'price' in df.columns
    assert df['price'].iloc[0] == 90.0
    mock_yfinance_success.assert_called_once_with("TEST.SA")
    mock_yfinance_success.return_value.history.assert_called_once()


def test_fetch_historical_data_uses_alpha_vantage_with_key(mock_alpha_vantage_success, monkeypatch):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV")
    monkeypatch.setattr("app.services.data_collector._api_call_cache", {})
    monkeypatch.setattr("app.services.data_collector._last_api_call_time_alpha_vantage", 0)

    df = fetch_historical_data("DUMMY.SA")
    assert df is not None
    assert df['price'].iloc[0] == 100.0
    mock_alpha_vantage_success.return_value.get_daily_adjusted.assert_called_with(symbol="DUMMY.SAO", outputsize='full')


@patch("app.services.data_collector._fetch_with_alpha_vantage", return_value=None)
def test_fetch_historical_data_falls_back_to_yfinance(mock_av_failed, mock_yfinance_success, monkeypatch):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", "TESTKEY_AV_FAIL")
    monkeypatch.setattr("app.services.data_collector._api_call_cache", {})

    df = fetch_historical_data("ANY.SA")
    mock_av_failed.assert_called_once()
    mock_yfinance_success.assert_called_once_with("ANY.SA")
    assert df is not None
    assert df['price'].iloc[0] == 90.0


def test_get_asset_data_sample_uses_fetch_historical(mock_yfinance_success, monkeypatch):
    monkeypatch.setattr(settings, "ALPHA_VANTAGE_API_KEY", None) # Ensure AV is not tried
    monkeypatch.setattr("app.services.data_collector._api_call_cache", {})

    df = get_asset_data_sample("SAMPLE.SA", n_points=2)
    assert df is not None
    assert len(df) == 2
    assert df['price'].iloc[0] == 91.0
    assert df['price'].iloc[1] == 92.0
```
