import pandas as pd
import numpy as np
import pytest # Import pytest for approx
from app.services.cointegration_analyzer import calculate_zscore, run_engle_granger_test

def test_calculate_zscore():
    # Test with a simple series
    series1 = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    zscore1 = calculate_zscore(series1)
    # Expected: (10 - 5.5) / np.std([1..10], ddof=0) for population if pandas default is ddof=1
    # Pandas std default is ddof=1. Our function uses pandas default.
    # Mean = 5.5. Std = np.std(series1, ddof=1) = 3.02765
    # Z = (10 - 5.5) / 3.02765 = 4.5 / 3.02765 = 1.4863
    assert zscore1 == pytest.approx(1.48630, abs=1e-5)


    # Test with rolling window
    series2 = pd.Series([1,1,1,1,1, 10,10,10,10,20], dtype=float) # Last point is 20
    # Window 5: data is [10,10,10,10,20]. Mean = 12. Std (ddof=1) = 4.472135955
    # Z = (20 - 12) / 4.472135955 = 8 / 4.472135955 = 1.788854382
    zscore2_window_5 = calculate_zscore(series2, window=5)
    assert zscore2_window_5 == pytest.approx(1.78885, abs=1e-5)

    # Test with empty series
    assert np.isnan(calculate_zscore(pd.Series([], dtype=float)))

    # Test with series with std == 0 (overall)
    assert np.isnan(calculate_zscore(pd.Series([5,5,5,5], dtype=float)))

    # Test with series with std == 0 (rolling window)
    series3 = pd.Series([1,2,3,5,5,5,5], dtype=float)
    assert np.isnan(calculate_zscore(series3, window=4)) # Window [5,5,5,5] has std 0

def test_run_engle_granger_test_basic():
    # Create two obviously cointegrated series (Y = 2*X + noise)
    np.random.seed(42)
    x_array = np.arange(100, dtype=float)
    noise = np.random.normal(0, 0.1, 100)
    y_array = 2 * x_array + 5 + noise

    # Create pandas Series with names, as the service function might use them
    x = pd.Series(x_array, name="X_series")
    y = pd.Series(y_array, name="Y_series")


    result = run_engle_granger_test(y, x)
    assert "error" not in result, f"Test failed with error: {result.get('error')}"
    assert result["p_value"] is not None
    assert result["p_value"] < 0.05 # Expect them to be cointegrated
    assert result["beta_coefficient"] == pytest.approx(2.0, abs=0.1) # Beta of X
    assert result["const_coefficient"] == pytest.approx(5.0, abs=0.1)
    assert result["n_observations"] == 100

def test_run_engle_granger_test_non_cointegrated():
    # Create two non-cointegrated series (e.g., two independent random walks)
    np.random.seed(123)
    x = pd.Series(np.cumsum(np.random.normal(0, 1, 100)), name="RandX")
    y = pd.Series(np.cumsum(np.random.normal(0, 1, 100)), name="RandY")

    result = run_engle_granger_test(y, x)
    assert "error" not in result, f"Test failed with error: {result.get('error')}"
    assert result["p_value"] is not None
    # P-value is expected to be high for non-cointegrated series
    assert result["p_value"] > 0.10 # Using a threshold like 0.10, could be 0.05

def test_run_engle_granger_insufficient_data():
    x = pd.Series(np.arange(10), name="ShortX")
    y = 2 * x + 5
    y.name = "ShortY"
    result = run_engle_granger_test(y, x)
    assert "error" in result
    assert "Not enough data points" in result["error"]

def test_run_engle_granger_perfect_collinearity_residuals_std_zero():
    # Test case where residuals might have zero standard deviation (perfect fit)
    x = pd.Series(np.arange(50), dtype=float, name="X_collinear")
    y = 2 * x
    y.name = "Y_collinear" # Perfect linear relationship, residuals should be close to zero

    result = run_engle_granger_test(y,x)
    # This should result in an error because residuals std will be (near) zero
    assert "error" in result
    assert "Residuals are constant" in result["error"] or "ADF test failed" in result["error"]

```
