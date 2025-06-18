import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from typing import Optional, Tuple, List, Dict, Any # Added Any for Dict value
from .data_collector import get_asset_data_sample

def run_engle_granger_test(series_y: pd.Series, series_x: pd.Series) -> Dict[str, Any]:
    """
    Performs the Engle-Granger two-step cointegration test.

    The regression performed is Y = Beta*X + Intercept. The residuals of this
    regression are then tested for stationarity using the Augmented Dickey-Fuller (ADF) test.

    Args:
        series_y: Pandas Series representing the dependent variable (Y). Index should be datetime.
        series_x: Pandas Series representing the independent variable (X). Index should be datetime.
                  Both series are assumed to be cleaned and aligned by their datetime index before calling.
                  Series names are used for parameter identification in OLS results if available.

    Returns:
        A dictionary containing:
            - "adf_statistic" (float): The ADF test statistic from the residuals test.
            - "p_value" (float): The p-value from the ADF test on residuals.
            - "critical_values" (Dict[str, float]): Critical values for the ADF test (e.g., "1%", "5%", "10%").
            - "beta_coefficient" (float | None): The hedge ratio (coefficient of X from OLS: Y = Beta*X + const). None if not calculable.
            - "const_coefficient" (float | None): The constant term (intercept) from the OLS regression. None if not calculable.
            - "n_observations" (int): Number of observations used in the ADF test (length of residuals).
            - "error" (str | None): An error message string if the test could not be performed or failed at a step.
    """
    if series_y.empty or series_x.empty:
        return {"error": "Input series cannot be empty."}
    if len(series_y) < 20:
         return {"error": f"Not enough data points to perform test (minimum 20 required, got {len(series_y)})."}

    y = series_y.astype(float)
    x_with_const = sm.add_constant(series_x.astype(float), has_constant='add') # Explicitly add constant

    model = sm.OLS(y, x_with_const)
    results = model.fit()

    residuals = results.resid

    if residuals.std() < 1e-9:
        return {"error": "Residuals are constant, ADF test cannot be performed."}

    try:
        adf_test_result = adfuller(residuals, autolag='AIC')
    except Exception as e:
        return {"error": f"ADF test failed on residuals: {str(e)}"}

    # Safely access params by checking existence or iloc if names are generic
    beta_coefficient = results.params.get(series_x.name, results.params.iloc[1] if len(results.params) > 1 else None)
    const_coefficient = results.params.get('const', results.params.iloc[0] if len(results.params) > 0 else None)

    return {
        "adf_statistic": adf_test_result[0],
        "p_value": adf_test_result[1],
        "critical_values": adf_test_result[4],
        "beta_coefficient": beta_coefficient,
        "const_coefficient": const_coefficient,
        "n_observations": len(residuals)
    }

def calculate_pair_value(series_y: pd.Series, series_x: pd.Series, beta_x: Optional[float] = None) -> pd.Series:
    """
    Calculates the value series for a pair, which can be either:
    1. Spread: Y - (beta * X)
    2. Ratio: Y / X (handles X=0 by replacing with NaN before division)

    Args:
        series_y: Pandas Series for asset Y.
        series_x: Pandas Series for asset X. (Must be aligned with series_y).
        beta_x: Optional hedge ratio (beta). If provided, calculates spread.
                If None, calculates ratio.

    Returns:
        A Pandas Series representing the calculated spread or ratio. Returns an empty Series if inputs are empty.
        The resulting series isname is not explicitly set here.
    """
    if series_y.empty or series_x.empty: return pd.Series(dtype=float)
    s_y_f, s_x_f = series_y.astype(float), series_x.astype(float)
    if beta_x is not None: return (s_y_f - beta_x * s_x_f).dropna()
    s_x_f_no_zero = s_x_f.replace(0, np.nan)
    return (s_y_f / s_x_f_no_zero).dropna()

def calculate_zscore(series: pd.Series, window: Optional[int] = None) -> float:
    """
    Calculates the Z-score of the last point in a given Pandas Series.

    The Z-score is calculated as: (last_value - mean) / std_dev.
    Mean and standard deviation can be calculated either for the entire series (if window is None or invalid)
    or using a rolling window of the specified size.

    Args:
        series: Pandas Series for which to calculate the Z-score. Must not be empty and have at least 2 points.
        window: Optional integer for the rolling window size. If None, less than 2, or greater than series length,
                the overall mean/std of the series is used.

    Returns:
        The calculated Z-score as a float. Returns np.nan if calculation is not possible
        (e.g., series too short, standard deviation is zero, or data issues).
    """
    if series.empty or len(series) < 2: return np.nan # Not enough data for mean/std calculation

    # Determine if rolling window should be used
    use_rolling = window is not None and window > 1 and window <= len(series)

    mean = series.rolling(window=window).mean().iloc[-1] if use_rolling else series.mean()
    std = series.rolling(window=window).std().iloc[-1] if use_rolling else series.std()
    if pd.isna(mean) or pd.isna(std) or std < 1e-9: return np.nan
    return (series.iloc[-1] - mean) / std

def identify_cointegrated_pairs(
    asset_tickers: List[str], p_value_threshold: float = 0.05,
    min_obs_for_test: int = 60, data_fetch_points: int = 312 # 252 + 60
) -> Dict[str, Any]:
    if not asset_tickers or len(asset_tickers) < 2:
        return {"summary": "At least two tickers are required.", "pairs": [], "processed_tickers_count": len(asset_tickers or [])}

    asset_data_map: Dict[str, pd.Series] = {}
    skipped_tickers: List[str] = []
    for ticker in asset_tickers:
        try:
            df = get_asset_data_sample(ticker, n_points=data_fetch_points)
            if not df.empty and 'price' in df.columns and len(df['price']) >= min_obs_for_test:
                asset_data_map[ticker] = df['price']
            else: skipped_tickers.append(ticker)
        except ValueError: skipped_tickers.append(ticker)

    processed_count = len(asset_data_map)
    if processed_count < 2:
        return {"summary": f"Not enough assets with data ({processed_count}/{len(asset_tickers)}). Skipped: {', '.join(skipped_tickers) or 'None'}.",
                "pairs": [], "processed_tickers_count": processed_count}

    results: List[Dict[str, Any]] = []
    unique_data_tickers = list(asset_data_map.keys())
    for i in range(processed_count):
        for j in range(processed_count):
            if i == j: continue
            ticker_y, ticker_x = unique_data_tickers[i], unique_data_tickers[j]
            s_y_raw, s_x_raw = asset_data_map[ticker_y], asset_data_map[ticker_x]

            aligned = pd.concat([s_y_raw.rename(ticker_y), s_x_raw.rename(ticker_x)], axis=1, join='inner').dropna()
            if len(aligned) < min_obs_for_test: continue
            s_y_aligned, s_x_aligned = aligned[ticker_y], aligned[ticker_x]

            test = run_engle_granger_test(s_y_aligned, s_x_aligned)
            if test.get("error") or test.get("n_observations", 0) < min_obs_for_test: continue

            if test["p_value"] is not None and test["p_value"] < p_value_threshold:
                beta = test.get('beta_coefficient')
                spread = calculate_pair_value(s_y_aligned, s_x_aligned, beta_x=beta)
                zscore = calculate_zscore(spread, window=60) if not spread.empty else np.nan
                results.append({
                    "pair_yx": (ticker_y, ticker_x), "adf_statistic": test["adf_statistic"],
                    "p_value": test["p_value"], "hedge_ratio_beta_x": beta,
                    "current_zscore_of_spread": zscore if pd.notna(zscore) else None,
                    "n_observations_in_test": test["n_observations"]
                })
    summary_msg = (f"Processed {processed_count}/{len(asset_tickers)} tickers. "
                   f"Skipped: {', '.join(skipped_tickers) or 'None'}. "
                   f"Found {len(results)} cointegrated (Y,X) configs.")
    return {"summary": summary_msg, "pairs": results, "processed_tickers_count": processed_count}
