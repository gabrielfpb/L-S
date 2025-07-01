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


from sqlalchemy.orm import Session # Added for type hinting db session
from .data_collector import fetch_historical_data # Use the real data fetcher
# pandas and numpy are already imported at the top

# Ensure MIN_OBS_FOR_API_EG_TEST is defined or accessible in this file
# It was defined in cointegration_routes.py, so might need to be moved to a shared consts file or config
MIN_OBS_FOR_API_EG_TEST = 20 # Define it here for now, ideally from a shared consts module


def get_historical_pair_data_for_charting(
    db: Session,
    ticker_y: str,
    ticker_x: str,
    start_date: datetime.date,
    end_date: datetime.date,
    z_score_window: int = 20,
    provided_hedge_ratio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Retrieves and processes historical data for a pair of tickers (Y, X) to be used in charting.

    This function performs the following steps:
    1. Fetches historical price data for `ticker_y` and `ticker_x` for the given date range.
    2. Aligns the data to common timestamps.
    3. Calculates the hedge ratio (Beta of X in Y = Beta*X + const) using Engle-Granger test
       on the initial segment of the data if `provided_hedge_ratio` is None.
    4. Calculates the spread series (Y - Beta*X).
    5. Calculates the rolling mean of the spread, Z-Score bands (+/-1 and +/-2 std dev),
       and the rolling Z-Score of the spread, using the specified `z_score_window`.

    Args:
        db: SQLAlchemy database session (currently unused but kept for future potential use,
            e.g., fetching pre-calculated hedge ratios or other metadata).
        ticker_y: Ticker symbol for the dependent asset (Y).
        ticker_x: Ticker symbol for the independent asset (X).
        start_date: Start date for the historical data period.
        end_date: End date for the historical data period.
        z_score_window: The rolling window size for Z-score and band calculations. Defaults to 20.
        provided_hedge_ratio: Optional pre-calculated hedge ratio. If None, it's recalculated.

    Returns:
        A dictionary containing various time series (prices, spread, mean, bands, Z-score)
        as lists of floats/None, a common list of timestamps (as datetime objects),
        the calculated hedge ratio, and an optional "error" key if issues occur.
        Keys in the dictionary align with `HistoricalPairDataResponse` Pydantic schema.
    """
    try:
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        # 1. Fetch historical price data for both tickers
        df_y_full = fetch_historical_data(ticker_y, start_date_str, end_date_str)
        df_x_full = fetch_historical_data(ticker_x, start_date_str, end_date_str)

        if df_y_full.empty or 'price' not in df_y_full.columns:
            return {"error": f"No price data found for {ticker_y} in the given range."}
        if df_x_full.empty or 'price' not in df_x_full.columns:
            return {"error": f"No price data found for {ticker_x} in the given range."}

        series_y_price = df_y_full['price']
        series_x_price = df_x_full['price']

        # 2. Align data by timestamp (inner join to get common dates)
        aligned_df = pd.concat([series_y_price.rename('Y'), series_x_price.rename('X')], axis=1, join='inner').dropna()
        if len(aligned_df) < z_score_window:
             return {"error": f"Not enough overlapping data points ({len(aligned_df)}) for Z-score window ({z_score_window})."}

        s_y = aligned_df['Y']
        s_x = aligned_df['X']

        # 3. Determine Hedge Ratio (Beta of X)
        beta_x = provided_hedge_ratio
        if beta_x is None:
            if len(s_y) < MIN_OBS_FOR_API_EG_TEST:
                 return {"error": f"Not enough data ({len(s_y)}) to reliably calculate hedge ratio for charting period."}

            eg_test_result = run_engle_granger_test(s_y, s_x)
            if eg_test_result.get("error"):
                return {"error": f"Hedge ratio calculation failed: {eg_test_result.get('error')}"}
            beta_x = eg_test_result.get("beta_coefficient")
            if beta_x is None: # Should not happen if no error from run_engle_granger_test and params are valid
                return {"error": "Could not determine hedge ratio (beta_x is None from EG test)."}

        # 4. Calculate Spread: Y - beta*X
        spread = calculate_pair_value(s_y, s_x, beta_x=beta_x)
        if spread.empty:
            return {"error": "Spread calculation resulted in empty series."}

        # 5. Calculate Rolling Mean, Std Dev for bands, and Z-Score for the spread
        if len(spread) < z_score_window: # Check again after spread calculation (though index should be same as s_y, s_x)
            return {"error": f"Spread series too short ({len(spread)}) for Z-score window ({z_score_window})."}

        spread_mean = spread.rolling(window=z_score_window, min_periods=z_score_window).mean()
        spread_std = spread.rolling(window=z_score_window, min_periods=z_score_window).std()

        z_score_series = (spread - spread_mean) / spread_std
        z_score_series.replace([np.inf, -np.inf], np.nan, inplace=True)

        final_index = spread_mean.dropna().index

        def to_list_safe(series: Optional[pd.Series], idx: pd.Index) -> List[Optional[float]]:
            if series is None or series.empty: return [None] * len(idx)
            return series.reindex(idx).replace({np.nan: None}).tolist()

        return {
            "ticker_y": ticker_y,
            "ticker_x": ticker_x,
            "timestamps": final_index.to_pydatetime().tolist(),
            "prices_y": to_list_safe(s_y, final_index),
            "prices_x": to_list_safe(s_x, final_index),
            "spread": to_list_safe(spread, final_index),
            "spread_mean": to_list_safe(spread_mean, final_index),
            "spread_std_dev_upper_1": to_list_safe(spread_mean + spread_std, final_index),
            "spread_std_dev_lower_1": to_list_safe(spread_mean - spread_std, final_index),
            "spread_std_dev_upper_2": to_list_safe(spread_mean + 2 * spread_std, final_index),
            "spread_std_dev_lower_2": to_list_safe(spread_mean - 2 * spread_std, final_index),
            "z_score": to_list_safe(z_score_series, final_index),
            "calculated_hedge_ratio_beta_x": beta_x
        }

    except Exception as e:
        # import traceback; traceback.print_exc() # Uncomment for server-side debugging
        return {"error": f"Failed to get historical pair data: {str(e)}"}
