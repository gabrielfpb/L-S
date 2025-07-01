import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date

from app.services.reporting_service import generate_backtest_data
# Assuming MIN_OBS_EG_TEST_BACKTEST is defined in reporting_service or imported there.
# For test, we can also patch it if needed, or ensure mock data meets criteria.

@pytest.fixture
def mock_db_session_reporting():
    return MagicMock()

@pytest.fixture
def mock_fetch_historical_for_backtest(monkeypatch):
    mock_fetch = MagicMock()

    idx = pd.date_range(start='2023-01-01', periods=100, freq='B') # ~5 months of data
    # Simulate data where Y = 2*X + const + noise, and spread has some mean-reverting pattern
    x_prices = np.linspace(50, 60, 100)
    # Add a sine wave to y_prices to make spread mean-reverting for test purposes
    noise = np.random.normal(0, 0.5, 100)
    y_prices = 2 * x_prices + 10 + noise + 5 * np.sin(np.linspace(0, 10 * np.pi, 100))

    df_y = pd.DataFrame({'price': y_prices}, index=idx)
    df_x = pd.DataFrame({'price': x_prices}, index=idx)

    def side_effect_func(ticker, sd, ed, force_refresh=False): # Match updated signature
        if ticker == "STOCK_Y.SA":
            return df_y[(df_y.index >= pd.to_datetime(sd)) & (df_y.index <= pd.to_datetime(ed))]
        elif ticker == "STOCK_X.SA":
            return df_x[(df_x.index >= pd.to_datetime(sd)) & (df_x.index <= pd.to_datetime(ed))]
        return pd.DataFrame(columns=['price','volume'])

    mock_fetch.side_effect = side_effect_func
    monkeypatch.setattr("app.services.reporting_service.fetch_historical_data", mock_fetch)
    return mock_fetch

@pytest.fixture
def mock_eg_test_for_backtest(monkeypatch):
    # This mock will be used for the initial beta calculation in generate_backtest_data
    mock_eg = MagicMock(return_value={
        "beta_coefficient": 2.0,
        "const_coefficient": 10.0,
        "p_value": 0.01, # Cointegrated
        "error": None # No error
    })
    monkeypatch.setattr("app.services.reporting_service.run_engle_granger_test", mock_eg)
    return mock_eg

def test_generate_backtest_data_simple_run(
    mock_db_session_reporting,
    mock_fetch_historical_for_backtest,
    mock_eg_test_for_backtest
):
    params = {
        "tickers": ["STOCK_Y.SA", "STOCK_X.SA"],
        "start_date": "2023-01-01", # Full range of mock data
        "end_date": "2023-05-26",   # Approx 100 business days
        "z_score_window": 20,
        "entry_z_threshold": 1.5,
        "exit_z_threshold": 0.2,
        "strategy_name": "test_zscore_strategy"
    }
    # Ensure MIN_OBS_EG_TEST_BACKTEST (60) + z_score_window (20) = 80 < 100 points from mock data

    results = generate_backtest_data(mock_db_session_reporting, user_id=1, params=params)

    assert "error" not in results, f"Backtest failed with error: {results.get('error')}"
    assert results["total_pnl_on_spread_units"] is not None
    assert results["number_of_trades"] >= 0
    assert "equity_curve_dates" in results
    assert "equity_curve_values" in results
    if results["number_of_trades"] > 0: # Some metrics only make sense if trades occurred
        assert len(results["equity_curve_dates"]) == len(results["equity_curve_values"])
        assert results["calculated_hedge_ratio_beta_x"] == pytest.approx(2.0)
        assert results["total_pnl_on_spread_units"] != 0 # Expect some P&L due to sine wave in mock data
        assert results["sharpe_ratio_approx"] is not None


def test_generate_backtest_data_insufficient_data(mock_db_session_reporting, mock_fetch_historical_for_backtest):
    # Make fetch_historical_data return fewer points than needed for beta + z-score window
    short_idx = pd.date_range(start='2023-01-01', periods=50, freq='B') # MIN_OBS_EG_TEST_BACKTEST is 60
    df_short = pd.DataFrame({'price': np.linspace(50, 55, 50)}, index=short_idx)
    mock_fetch_historical_for_backtest.side_effect = lambda t, sd, ed, fr=False: df_short

    params = {
        "tickers": ["SHORT_Y.SA", "SHORT_X.SA"],
        "start_date": "2023-01-01", "end_date": "2023-03-10", # Approx 50 days
        "z_score_window": 20
    }
    results = generate_backtest_data(mock_db_session_reporting, user_id=1, params=params)
    assert "error" in results
    assert "Overlap data too short" in results["error"]

def test_generate_backtest_data_beta_calc_error(
    mock_db_session_reporting,
    mock_fetch_historical_for_backtest,
    mock_eg_test_for_backtest
):
    mock_eg_test_for_backtest.return_value = {"error": "Simulated EG test error"}
    params = {
        "tickers": ["STOCK_Y.SA", "STOCK_X.SA"],
        "start_date": "2023-01-01", "end_date": "2023-05-26",
        "z_score_window": 20
    }
    results = generate_backtest_data(mock_db_session_reporting, user_id=1, params=params)
    assert "error" in results
    assert "Hedge ratio calculation failed" in results["error"]

```
