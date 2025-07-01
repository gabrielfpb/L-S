import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from app.services.cointegration_analyzer import (
    calculate_zscore,
    run_engle_granger_test,
    get_historical_pair_data_for_charting,
    MIN_OBS_FOR_API_EG_TEST
)
from app.services import cointegration_analyzer as ca_module

# Existing tests for calculate_zscore and run_engle_granger_test
def test_calculate_zscore():
    series1 = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    zscore1 = calculate_zscore(series1)
    assert zscore1 == pytest.approx(1.48630, abs=1e-5)

    series2 = pd.Series([1,1,1,1,1, 10,10,10,10,20], dtype=float)
    zscore2_window_5 = calculate_zscore(series2, window=5)
    assert zscore2_window_5 == pytest.approx(1.78885, abs=1e-5)

    assert np.isnan(calculate_zscore(pd.Series([], dtype=float)))
    assert np.isnan(calculate_zscore(pd.Series([5,5,5,5], dtype=float)))
    series3 = pd.Series([1,2,3,5,5,5,5], dtype=float)
    assert np.isnan(calculate_zscore(series3, window=4))


def test_run_engle_granger_test_basic():
    np.random.seed(42)
    x_array = np.arange(100, dtype=float)
    noise = pd.Series(np.random.normal(0, 0.1, 100))
    y_array = 2 * x_array + 5 + noise
    x = pd.Series(x_array, name="X_series")
    y = pd.Series(y_array, name="Y_series")

    result = run_engle_granger_test(y, x)
    assert "error" not in result, f"Test failed with error: {result.get('error')}"
    assert result["p_value"] is not None and result["p_value"] < 0.05
    assert result["beta_coefficient"] == pytest.approx(2.0, abs=0.1)
    assert result["const_coefficient"] == pytest.approx(5.0, abs=0.1)
    assert result["n_observations"] == 100

def test_run_engle_granger_test_non_cointegrated():
    np.random.seed(123)
    x = pd.Series(np.cumsum(np.random.normal(0, 1, 100)), name="RandX")
    y = pd.Series(np.cumsum(np.random.normal(0, 1, 100)), name="RandY")
    result = run_engle_granger_test(y, x)
    assert "error" not in result
    assert result["p_value"] is not None and result["p_value"] > 0.10

def test_run_engle_granger_insufficient_data():
    # MIN_OBS_FOR_API_EG_TEST is imported from the module, should be 20
    x = pd.Series(np.arange(MIN_OBS_FOR_API_EG_TEST - 1), name="ShortX", dtype=float)
    y = 2 * x + 5
    y.name = "ShortY"
    result = run_engle_granger_test(y, x)
    assert "error" in result
    assert "Not enough data points" in result["error"]

def test_run_engle_granger_perfect_collinearity_residuals_std_zero():
    x = pd.Series(np.arange(50), dtype=float, name="X_collinear")
    y = 2 * x
    y.name = "Y_collinear"
    result = run_engle_granger_test(y,x)
    assert "error" in result
    assert "Residuals are constant" in result["error"] or "ADF test failed" in result["error"]

# --- New tests for get_historical_pair_data_for_charting ---

@pytest.fixture
def mock_db_session_coint_analyzer():
    return MagicMock()

@pytest.fixture
def mock_fetch_historical_data_for_charting(monkeypatch):
    mock_fetch = MagicMock()
    idx = pd.date_range(start='2023-01-01', periods=100, freq='B')
    df_y_data = {'price': np.linspace(100, 150, 100)}
    df_x_data = {'price': np.linspace(50, 75, 100)}

    def side_effect_func(ticker, sd, ed, force_refresh=False):
        if ticker == "CHART_Y.SA":
            return pd.DataFrame(df_y_data, index=idx)
        elif ticker == "CHART_X.SA":
            return pd.DataFrame(df_x_data, index=idx)
        # Return empty DataFrame with 'price' column for other tickers to avoid None.
        return pd.DataFrame(columns=['price', 'volume'], index=pd.to_datetime([]))


    mock_fetch.side_effect = side_effect_func
    monkeypatch.setattr("app.services.cointegration_analyzer.fetch_historical_data", mock_fetch)
    return mock_fetch

@pytest.fixture
def mock_run_engle_granger_for_charting(monkeypatch):
    mock_eg = MagicMock(return_value={
        "adf_statistic": -3.5, "p_value": 0.04, "critical_values": {"1%": -3.5},
        "beta_coefficient": 2.0, "const_coefficient": 5.0, "n_observations": MIN_OBS_FOR_API_EG_TEST
    })
    monkeypatch.setattr("app.services.cointegration_analyzer.run_engle_granger_test", mock_eg)
    return mock_eg

def test_get_historical_pair_data_success(mock_db_session_coint_analyzer, mock_fetch_historical_data_for_charting, mock_run_engle_granger_for_charting):
    result = get_historical_pair_data_for_charting(
        db=mock_db_session_coint_analyzer,
        ticker_y="CHART_Y.SA", ticker_x="CHART_X.SA",
        start_date=date(2023,1,1), end_date=date(2023,5,26),
        z_score_window=20
    )

    assert "error" not in result, f"Result contained error: {result.get('error')}"
    assert result["ticker_y"] == "CHART_Y.SA"
    assert len(result["timestamps"]) == 100 - (20 - 1)
    assert result["calculated_hedge_ratio_beta_x"] == pytest.approx(2.0)
    mock_fetch_historical_data_for_charting.assert_any_call("CHART_Y.SA", "2023-01-01", "2023-05-26")
    mock_run_engle_granger_for_charting.assert_called_once()

def test_get_historical_pair_data_insufficient_data_for_zscore_window(mock_db_session_coint_analyzer, mock_fetch_historical_data_for_charting, mock_run_engle_granger_for_charting):
    idx_short = pd.date_range(start='2023-01-01', periods=10, freq='B')
    df_short = pd.DataFrame({'price': np.linspace(100,105,10)}, index=idx_short)
    mock_fetch_historical_data_for_charting.side_effect = lambda ticker, sd, ed, force_refresh=False: df_short

    result = get_historical_pair_data_for_charting(
        db=mock_db_session_coint_analyzer,
        ticker_y="SHORT_Y.SA", ticker_x="SHORT_X.SA",
        start_date=date(2023,1,1), end_date=date(2023,1,15),
        z_score_window=20
    )
    assert "error" in result
    assert "Not enough overlapping data points" in result["error"] or "Spread series too short" in result["error"]

def test_get_historical_pair_data_beta_calc_fails(mock_db_session_coint_analyzer, mock_fetch_historical_data_for_charting, mock_run_engle_granger_for_charting):
    mock_run_engle_granger_for_charting.return_value = {"error": "EG test failed"}
    result = get_historical_pair_data_for_charting(
        db=mock_db_session_coint_analyzer, ticker_y="CHART_Y.SA", ticker_x="CHART_X.SA",
        start_date=date(2023,1,1), end_date=date(2023,5,26), z_score_window=20
    )
    assert "error" in result
    assert "Hedge ratio calculation failed" in result["error"]

def test_get_historical_pair_data_fetch_fails_for_one_ticker(mock_db_session_coint_analyzer, mock_fetch_historical_data_for_charting):
    def side_effect_fetch_fail(ticker, sd, ed, force_refresh=False):
        if ticker == "FAIL.SA":
            return pd.DataFrame(columns=['price','volume'], index=pd.to_datetime([])) # Empty with columns
        return pd.DataFrame({'price': np.random.rand(50)}, index=pd.date_range('20230101', periods=50))

    mock_fetch_historical_data_for_charting.side_effect = side_effect_fetch_fail

    result = get_historical_pair_data_for_charting(
        db=mock_db_session_coint_analyzer, ticker_y="Y.SA", ticker_x="FAIL.SA",
        start_date=date(2023,1,1), end_date=date(2023,12,31), z_score_window=20
    )
    assert "error" in result
    assert "No price data found for FAIL.SA" in result["error"]

```
