import pytest
from unittest.mock import patch, MagicMock, mock_open, call, ANY
import pandas as pd
import numpy as np
from datetime import date, datetime, timezone
import os
import json

from app.services.reporting_service import (
    generate_report_files,
    generate_html_for_pdf,
    generate_backtest_data, # Ensure this is imported
    REPORTS_STORAGE_DIR
)
from app.core.config import settings


# --- Fixtures ---
@pytest.fixture
def mock_db_session_reporting():
    return MagicMock()

@pytest.fixture(autouse=True) # Apply to all tests in this module that might use REPORTS_STORAGE_DIR
def temp_reports_storage(monkeypatch, tmp_path):
    # Use pytest's tmp_path for a unique temporary directory per test function
    d = tmp_path / "generated_reports_test_scope"
    d.mkdir()
    monkeypatch.setattr("app.services.reporting_service.REPORTS_STORAGE_DIR", str(d))
    return str(d)


@pytest.fixture
def sample_report_data_backtest(): # Removed monkeypatch for os.makedirs, handled by temp_reports_storage
    return {
        "parameters_used": {"tickers": ["Y.SA", "X.SA"], "start_date": "2023-01-01", "strategy_name": "TestStrat"},
        "calculated_hedge_ratio_beta_x": 1.95,
        "total_pnl_on_spread_units": 1250.75,
        "number_of_trades": 10,
        "win_rate": 0.6,
        "equity_curve_dates": [date(2023,1,1).isoformat(), date(2023,1,2).isoformat()],
        "equity_curve_values": [100000.0, 100150.0],
        "trades_log_sample": [
            {"type": "ENTRY_LONG_SPREAD", "date": datetime(2023,1,1,10,0,0, tzinfo=timezone.utc).isoformat(), "spread_price": 10.5, "z_score": -2.1, "pnl":0.0},
            {"type": "EXIT_LONG_SPREAD", "date": datetime(2023,1,2,15,0,0, tzinfo=timezone.utc).isoformat(), "spread_price": 11.0, "z_score": -0.5, "pnl": 0.5}
        ]
    }

# --- Tests for generate_html_for_pdf and generate_report_files ---

def test_generate_html_for_pdf_structure(sample_report_data_backtest):
    html = generate_html_for_pdf("My Backtest", "BACKTEST", sample_report_data_backtest)
    assert "<html>" in html; assert "<meta charset='UTF-8'>" in html
    assert "<h1>Report: My Backtest</h1>" in html
    assert "<h2>Parameters Used</h2>" in html
    assert "<td>Tickers</td><td>['Y.SA', 'X.SA']</td>" in html
    assert "<h2>Summary Metrics</h2>" in html
    assert "<td>Total Pnl On Spread Units</td><td>1250.7500</td>" in html
    assert "<h2 class='page-break'>Equity Curve Data</h2>" in html
    assert "<td>100150.00</td>" in html
    assert "<h2 class='page-break'>Sample Trades Log</h2>" in html
    assert "<th>Type</th>" in html
    assert "<td>ENTRY_LONG_SPREAD</td>" in html


@patch("app.services.reporting_service.pisa.CreatePDF")
@patch("builtins.open", new_callable=mock_open)
@patch("app.services.reporting_service.pd.Series.to_frame")
@patch("app.services.reporting_service.pd.DataFrame.to_csv")
def test_generate_report_files_creates_csv_and_pdf(
    mock_df_to_csv, mock_series_to_frame, mock_builtin_open, mock_create_pdf,
    sample_report_data_backtest, temp_reports_storage # Use the temp_reports_storage fixture
):
    mock_df_instance = MagicMock()
    mock_series_to_frame.return_value = mock_df_instance
    mock_pisa_status = MagicMock(); mock_pisa_status.err = 0
    mock_create_pdf.return_value = mock_pisa_status

    report_id = 123; report_name = "Test Report Detailed"
    pdf_filename_rel, csv_filename_rel = generate_report_files(
        report_id, report_name, sample_report_data_backtest, "BACKTEST"
    )

    safe_report_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in report_name).rstrip().replace(' ', '_')
    expected_base_filename = f"{safe_report_name}_{report_id}"
    expected_csv_filename = f"{expected_base_filename}.csv"
    expected_pdf_filename = f"{expected_base_filename}.pdf"

    assert csv_filename_rel == expected_csv_filename
    assert pdf_filename_rel == expected_pdf_filename

    csv_abs_path = os.path.join(temp_reports_storage, expected_csv_filename)
    pdf_abs_path = os.path.join(temp_reports_storage, expected_pdf_filename)

    # Check open calls were made for the correct files
    # This part can be tricky if other files are opened (like HTML debug on PDF fail)
    # For simplicity, we check that our main files were part of the calls.
    csv_open_called = False
    pdf_open_called = False
    for single_call in mock_builtin_open.call_args_list:
        args, kwargs = single_call
        if args[0] == csv_abs_path and args[1] == 'w': csv_open_called = True
        if args[0] == pdf_abs_path and args[1] == 'wb': pdf_open_called = True
    assert csv_open_called, "CSV file was not opened correctly."
    assert pdf_open_called, "PDF file was not opened correctly."

    mock_series_to_frame.assert_called()
    mock_df_instance.to_csv.assert_any_call(mock_builtin_open.return_value, header=True)
    assert mock_df_to_csv.call_count >= 2 # Equity curve and trades log
    mock_create_pdf.assert_called_once()


@patch("app.services.reporting_service.pisa.CreatePDF")
@patch("builtins.open", new_callable=mock_open)
def test_generate_report_files_pdf_creation_fails(
    mock_open_write, mock_create_pdf, sample_report_data_backtest, temp_reports_storage
):
    mock_pisa_status = MagicMock(); mock_pisa_status.err = 1; mock_pisa_status.errCode = "SimulatedError"
    mock_create_pdf.return_value = mock_pisa_status

    report_id = 456; report_name = "PDF Fail Test Report"
    pdf_filename_rel, csv_filename_rel = generate_report_files(
        report_id, report_name, sample_report_data_backtest, "SUMMARY"
    )

    assert pdf_filename_rel is None
    assert csv_filename_rel is not None

    safe_report_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in report_name).rstrip().replace(' ', '_')
    expected_base_filename = f"{safe_report_name}_{report_id}"
    html_debug_filename = f"{expected_base_filename}_debug.html"
    html_abs_path = os.path.join(temp_reports_storage, html_debug_filename)
    mock_open_write.assert_any_call(html_abs_path, "w", encoding="utf-8")


# --- Existing tests for generate_backtest_data (from previous plan) ---
@pytest.fixture
def mock_fetch_historical_for_backtest(monkeypatch):
    mock_fetch = MagicMock()
    idx = pd.date_range(start='2023-01-01', periods=100, freq='B')
    x_prices = np.linspace(50, 60, 100)
    noise = np.random.normal(0, 0.5, 100)
    y_prices = 2 * x_prices + 10 + noise + 5 * np.sin(np.linspace(0, 10 * np.pi, 100))
    df_y = pd.DataFrame({'price': y_prices}, index=idx)
    df_x = pd.DataFrame({'price': x_prices}, index=idx)
    def side_effect_func(ticker, sd, ed, force_refresh=False):
        if ticker == "STOCK_Y.SA": return df_y[(df_y.index >= pd.to_datetime(sd)) & (df_y.index <= pd.to_datetime(ed))]
        elif ticker == "STOCK_X.SA": return df_x[(df_x.index >= pd.to_datetime(sd)) & (df_x.index <= pd.to_datetime(ed))]
        return pd.DataFrame(columns=['price','volume'])
    mock_fetch.side_effect = side_effect_func
    monkeypatch.setattr("app.services.reporting_service.fetch_historical_data", mock_fetch)
    return mock_fetch

@pytest.fixture
def mock_eg_test_for_backtest(monkeypatch):
    mock_eg = MagicMock(return_value={"beta_coefficient": 2.0, "const_coefficient": 10.0, "p_value": 0.01, "error": None})
    monkeypatch.setattr("app.services.reporting_service.run_engle_granger_test", mock_eg)
    return mock_eg

def test_generate_backtest_data_simple_run(
    mock_db_session_reporting, mock_fetch_historical_for_backtest, mock_eg_test_for_backtest
):
    params = {
        "tickers": ["STOCK_Y.SA", "STOCK_X.SA"], "start_date": "2023-01-01", "end_date": "2023-05-26",
        "z_score_window": 20, "entry_z_threshold": 1.5, "exit_z_threshold": 0.2, "strategy_name": "test_zscore_strategy"
    }
    results = generate_backtest_data(mock_db_session_reporting, user_id=1, params=params)
    assert "error" not in results, f"Backtest error: {results.get('error')}"
    assert results["total_pnl_on_spread_units"] is not None; assert results["number_of_trades"] >= 0
    assert "equity_curve_dates" in results; assert "equity_curve_values" in results
    if results["number_of_trades"] > 0:
        assert len(results["equity_curve_dates"]) == len(results["equity_curve_values"])
        assert results["calculated_hedge_ratio_beta_x"] == pytest.approx(2.0)
        assert results["total_pnl_on_spread_units"] != 0
        assert results["sharpe_ratio_approx"] is not None
```
