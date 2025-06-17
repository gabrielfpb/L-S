from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict, Any

class CointegrationTestParams(BaseModel):
    ticker_y: str = Field(..., description="Ticker symbol for the dependent asset (Y).")
    ticker_x: str = Field(..., description="Ticker symbol for the independent asset (X).")

class CointegrationTestResult(BaseModel):
    pair_tested_yx: Tuple[str, str] = Field(description="Pair tested as (Y, X)")
    adf_statistic: Optional[float] = None
    p_value: Optional[float] = None
    critical_values: Optional[Dict[str, float]] = None
    is_cointegrated: Optional[bool] = Field(description="True if p_value < 0.05 (example threshold)")
    hedge_ratio_beta_x: Optional[float] = Field(None, description="Beta coefficient of X from OLS: Y = Beta*X + const")
    ols_constant: Optional[float] = Field(None, description="Constant term from OLS regression")
    n_observations: Optional[int] = None
    error: Optional[str] = None

class PairZScoreParams(BaseModel):
    ticker_y: str = Field(..., description="Ticker for the first asset in spread/ratio (Y).")
    ticker_x: str = Field(..., description="Ticker for the second asset in spread/ratio (X).")
    window: Optional[int] = Field(default=60, description="Rolling window for Z-score (min 2). If None or invalid (e.g. <=1), overall Z-score used.")
    use_spread_with_eg_beta: bool = Field(default=True, description="True: Z-score on spread (Y - Beta*X) using Beta from fresh EG test. False: Z-score on simple ratio (Y/X).")

class PairZScoreResponse(BaseModel):
    pair_analyzed_yx: Tuple[str, str] = Field(description="Pair analyzed as (Y,X)")
    value_type: str = Field(description="'spread (Y-Beta*X)' or 'ratio (Y/X)'")
    current_value: Optional[float] = Field(description="The latest value of the spread or ratio")
    z_score: Optional[float] = None
    series_mean_used_for_zscore: Optional[float] = Field(description="Mean of the (spread/ratio) series used for Z-score")
    series_std_dev_used_for_zscore: Optional[float] = Field(description="Std Dev of the (spread/ratio) series used for Z-score")
    hedge_ratio_beta_x_used: Optional[float] = Field(None, description="Beta of X if spread was used")
    error: Optional[str] = None

class IdentifyPairsRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=2, description="List of tickers to find cointegrated pairs from.")
    p_value_threshold: Optional[float] = Field(default=0.05, gt=0, lt=1)
    min_observations_for_test: Optional[int] = Field(default=60, gt=19, description="Min overlapping data points for EG test.")
    data_points_to_fetch: Optional[int] = Field(default=312, gt=20) # 252 + 60

class IdentifiedPairData(BaseModel):
    pair_yx: Tuple[str, str] = Field(description="Cointegrated pair (Y, X)")
    adf_statistic: float
    p_value: float
    hedge_ratio_beta_x: Optional[float] = Field(description="Beta of X for spread Y - Beta*X")
    current_zscore_of_spread: Optional[float] = Field(description="Z-score of the spread (Y - Beta*X) using a default window (e.g. 60 periods)")
    n_observations_in_test: int

class IdentifyPairsResponse(BaseModel):
    summary_message: str
    requested_tickers_count: int
    processed_tickers_with_data_count: int
    found_pairs_count: int
    pairs: List[IdentifiedPairData]
    parameters_used: IdentifyPairsRequest
