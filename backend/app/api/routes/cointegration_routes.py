from fastapi import APIRouter, HTTPException
from typing import List, Tuple, Dict, Any
from ..services import cointegration_analyzer as ca
from ..services import data_collector as dc
from ..api.schemas.cointegration_schemas import (
    CointegrationTestParams, CointegrationTestResult,
    PairZScoreParams, PairZScoreResponse,
    IdentifyPairsRequest, IdentifyPairsResponse, IdentifiedPairData
)
import pandas as pd
import numpy as np # For np.nan checks

router = APIRouter()

DEFAULT_API_DATA_POINTS = 312 # 252 + 60
MIN_OBS_FOR_API_EG_TEST = 20

async def _get_aligned_series_http(ticker_y: str, ticker_x: str, data_points: int) -> Tuple[pd.Series, pd.Series]:
    try:
        sy_df = dc.get_asset_data_sample(ticker_y, n_points=data_points)
        sx_df = dc.get_asset_data_sample(ticker_x, n_points=data_points)
    except ValueError as e: raise HTTPException(status_code=404, detail=f"Data collect error: {e}")
    if any(df.empty or 'price' not in df for df in [sy_df, sx_df]):
        raise HTTPException(status_code=404, detail=f"Price data missing for {ticker_y} or {ticker_x}")

    aligned = pd.concat([sy_df['price'].rename(ticker_y), sx_df['price'].rename(ticker_x)], axis=1, join='inner').dropna()
    if len(aligned) < 2: raise HTTPException(status_code=400, detail=f"Overlap < 2 for {ticker_y},{ticker_x}")
    return aligned[ticker_y], aligned[ticker_x]

@router.post("/cointegration/test", response_model=CointegrationTestResult)
async def api_run_cointegration_test(params: CointegrationTestParams):
    try:
        s_y, s_x = await _get_aligned_series_http(params.ticker_y, params.ticker_x, DEFAULT_API_DATA_POINTS)
        if len(s_y) < MIN_OBS_FOR_API_EG_TEST:
            raise HTTPException(status_code=400, detail=f"Need {MIN_OBS_FOR_API_EG_TEST} obs, got {len(s_y)}")

        res = ca.run_engle_granger_test(s_y, s_x)
        if res.get("error"): raise HTTPException(status_code=400, detail=f"Test fail: {res['error']}")

        is_coint = res["p_value"] is not None and res["p_value"] < 0.05
        return CointegrationTestResult(
            pair_tested_yx=(params.ticker_y, params.ticker_x), adf_statistic=res["adf_statistic"],
            p_value=res["p_value"], critical_values=res.get("critical_values"), is_cointegrated=is_coint,
            hedge_ratio_beta_x=res.get("beta_coefficient"), ols_constant=res.get("const_coefficient"),
            n_observations=res.get("n_observations")
        )
    except HTTPException as http_exc: raise http_exc
    except Exception as e: raise HTTPException(status_code=500, detail=f"Server error: {e}")

@router.post("/cointegration/zscore", response_model=PairZScoreResponse)
async def api_get_pair_zscore(params: PairZScoreParams):
    try:
        win = params.window if params.window is not None and params.window > 1 else 60
        pts = win + 200 # Ensure enough data for initial window and some history
        s_y, s_x = await _get_aligned_series_http(params.ticker_y, params.ticker_x, pts)

        beta_x = None
        val_type = "ratio (Y/X)"
        if params.use_spread_with_eg_beta:
            val_type = "spread (Y-Beta*X)"
            if len(s_y) < MIN_OBS_FOR_API_EG_TEST: # Ensure enough data for EG test if beta is needed
                return PairZScoreResponse(pair_analyzed_yx=(params.ticker_y,params.ticker_x), value_type=val_type, error=f"Data < {MIN_OBS_FOR_API_EG_TEST} for EG Beta (has {len(s_y)})")

            eg_res = ca.run_engle_granger_test(s_y, s_x)
            if eg_res.get("error"):
                return PairZScoreResponse(pair_analyzed_yx=(params.ticker_y,params.ticker_x), value_type=val_type, error=f"EG Beta fail: {eg_res['error']}")
            beta_x = eg_res.get("beta_coefficient")
            if beta_x is None:
                 return PairZScoreResponse(pair_analyzed_yx=(params.ticker_y,params.ticker_x), value_type=val_type, error="EG Beta was None")

        target_series = ca.calculate_pair_value(s_y, s_x, beta_x=beta_x)
        if target_series.empty or len(target_series) < 2:
            return PairZScoreResponse(pair_analyzed_yx=(params.ticker_y,params.ticker_x), value_type=val_type, hedge_ratio_beta_x_used=beta_x,
                                      error=f"Target series < 2 for Z-score (len {len(target_series)})")

        # Adjust window for z-score if it's too large for the available target_series length
        actual_zscore_window = min(win, len(target_series)) if win else None

        z = ca.calculate_zscore(target_series, actual_zscore_window)
        use_roll = actual_zscore_window is not None and actual_zscore_window > 1 and actual_zscore_window <= len(target_series)

        # Calculate mean and std based on the same windowing logic as calculate_zscore
        if use_roll:
            m = target_series.rolling(window=actual_zscore_window).mean().iloc[-1]
            s = target_series.rolling(window=actual_zscore_window).std().iloc[-1]
        else: # Overall mean/std
            m = target_series.mean()
            s = target_series.std()

        return PairZScoreResponse(
            pair_analyzed_yx=(params.ticker_y, params.ticker_x), value_type=val_type,
            current_value=target_series.iloc[-1] if not target_series.empty else None,
            z_score=z if pd.notna(z) else None, series_mean_used_for_zscore=m if pd.notna(m) else None,
            series_std_dev_used_for_zscore=s if pd.notna(s) else None, hedge_ratio_beta_x_used=beta_x
        )
    except HTTPException as http_exc: raise http_exc
    except Exception as e: raise HTTPException(status_code=500, detail=f"Server error Z-score: {e}")

@router.post("/cointegration/identify_pairs", response_model=IdentifyPairsResponse)
async def api_identify_cointegrated_pairs(params: IdentifyPairsRequest):
    try:
        res_dict = ca.identify_cointegrated_pairs(
            params.tickers, params.p_value_threshold,
            params.min_observations_for_test, params.data_points_to_fetch
        )
        pair_data = [IdentifiedPairData(**p) for p in res_dict.get("pairs", [])]
        return IdentifyPairsResponse(
            summary_message=res_dict.get("summary", "Done."),
            requested_tickers_count=len(params.tickers),
            processed_tickers_with_data_count=res_dict.get("processed_tickers_count",0),
            found_pairs_count=len(pair_data), pairs=pair_data, parameters_used=params
        )
    except Exception as e: raise HTTPException(status_code=500, detail=f"Server error identify: {e}")
