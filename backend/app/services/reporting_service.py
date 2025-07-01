from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
import datetime
import json
import os
import pandas as pd
import numpy as np

from ..models.models import ReportMetadata, Trade, User
from ..core.config import settings
from .data_collector import fetch_historical_data
# Import necessary functions from cointegration_analyzer
from .cointegration_analyzer import run_engle_granger_test, calculate_pair_value, MIN_OBS_FOR_API_EG_TEST as COINT_MIN_OBS_EG_TEST


REPORTS_STORAGE_DIR = getattr(settings, "REPORTS_STORAGE_DIR", "generated_reports")
if not os.path.exists(REPORTS_STORAGE_DIR):
    os.makedirs(REPORTS_STORAGE_DIR, exist_ok=True)

def create_report_metadata_entry(
    db: Session, report_type: str, user_id: Optional[int] = None,
    parameters: Optional[Dict[str, Any]] = None, celery_task_id: Optional[str] = None,
    report_name: Optional[str] = None
) -> ReportMetadata:
    if not report_name:
        report_name = f"{report_type.lower().replace('_', '-')}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}"
    db_report = ReportMetadata(
        report_name=report_name, report_type=report_type, user_id=user_id,
        parameters=parameters, status="PENDING", celery_task_id=celery_task_id
    )
    db.add(db_report); db.commit(); db.refresh(db_report)
    return db_report

def update_report_status(
    db: Session, report_id: int, status: str, error_message: Optional[str] = None,
    summary_data: Optional[Dict[str, Any]] = None, file_path_pdf: Optional[str] = None,
    file_path_csv: Optional[str] = None, generation_started_at: Optional[datetime.datetime] = None,
    generation_completed_at: Optional[datetime.datetime] = None,
) -> Optional[ReportMetadata]:
    db_report = db.query(ReportMetadata).filter(ReportMetadata.id == report_id).first()
    if db_report:
        db_report.status = status
        if error_message: db_report.error_message = error_message
        if summary_data: db_report.summary_data = summary_data
        if file_path_pdf: db_report.file_path_pdf = file_path_pdf
        if file_path_csv: db_report.file_path_csv = file_path_csv
        if generation_started_at: db_report.generation_started_at = generation_started_at
        if generation_completed_at: db_report.generation_completed_at = generation_completed_at
        db.commit(); db.refresh(db_report)
    return db_report

def get_report_metadata_by_id(db: Session, report_id: int) -> Optional[ReportMetadata]:
    return db.query(ReportMetadata).filter(ReportMetadata.id == report_id).first()

def list_reports_metadata(
    db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[ReportMetadata]:
    query = db.query(ReportMetadata)
    if user_id: query = query.filter(ReportMetadata.user_id == user_id)
    return query.order_by(ReportMetadata.generation_requested_at.desc()).offset(skip).limit(limit).all()

def generate_performance_summary_data(db: Session, user_id: Optional[int], period: str = "DAILY") -> Dict[str, Any]:
    end_date = datetime.datetime.now(datetime.timezone.utc)
    if period.upper() == "DAILY": start_date = end_date - datetime.timedelta(days=1)
    elif period.upper() == "WEEKLY": start_date = end_date - datetime.timedelta(weeks=1)
    else: start_date = end_date - datetime.timedelta(days=1)
    query = db.query(Trade).filter(Trade.status == "CLOSED", Trade.exit_datetime >= start_date, Trade.exit_datetime <= end_date)
    if user_id: query = query.filter(Trade.user_id == user_id)
    closed_trades = query.all()
    total_pnl = sum(t.realized_pnl for t in closed_trades if t.realized_pnl is not None)
    num_trades = len(closed_trades)
    winning_trades = sum(1 for t in closed_trades if t.realized_pnl is not None and t.realized_pnl > 0)
    losing_trades = sum(1 for t in closed_trades if t.realized_pnl is not None and t.realized_pnl < 0)
    return {
        "period": period.upper(), "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        "user_id": user_id if user_id else "All Users", "total_pnl": total_pnl,
        "number_of_trades_closed": num_trades, "winning_trades": winning_trades, "losing_trades": losing_trades,
        "win_rate": (winning_trades / num_trades) if num_trades > 0 else 0.0, # Ensure float division
    }

def generate_report_files(report_id: int, report_name: str, data: Dict[str, Any], report_type: str) -> Tuple[Optional[str], Optional[str]]:
    # Sanitize report_name for use in filename
    safe_report_name = report_name.replace(' ', '_').replace('/', '-').replace(':', '')
    base_filename = f"{safe_report_name}_{report_id}"

    json_content = json.dumps(data, indent=4, default=str) # Use default=str for datetime, etc.

    # For CSV: Try to make a more useful CSV from list of trades or similar structures
    csv_filename = f"{base_filename}.csv"
    csv_filepath = os.path.join(REPORTS_STORAGE_DIR, csv_filename)
    try:
        # Check if data contains a list of dicts (e.g., trades_log_sample)
        # Or if equity curve data is present and suitable for CSV
        if 'trades_log_sample' in data and isinstance(data['trades_log_sample'], list):
            pd.DataFrame(data['trades_log_sample']).to_csv(csv_filepath, index=False)
        elif 'equity_curve_dates' in data and 'equity_curve_values' in data:
            df_equity = pd.DataFrame({'date': data['equity_curve_dates'], 'equity': data['equity_curve_values']})
            df_equity.to_csv(csv_filepath, index=False)
        elif isinstance(data, dict) and data: # Fallback for simple dict
            # Convert dict to a DataFrame with 'key' and 'value' columns
            pd.Series(data).reset_index().rename(columns={'index': 'key', 0: 'value'}).to_csv(csv_filepath, index=False)
        else: # If data is not a dict or list of dicts, just write the JSON string
            with open(csv_filepath, 'w') as f:
                f.write(json_content)
        print(f"Generated placeholder CSV: {csv_filepath}")
    except Exception as e:
        print(f"Error generating CSV for report {report_id}: {e}")
        csv_filepath = None # Ensure path is None if generation fails

    # For PDF (still saving as .txt with JSON content as placeholder)
    pdf_filename = f"{base_filename}.pdf.txt"
    pdf_filepath = os.path.join(REPORTS_STORAGE_DIR, pdf_filename)
    try:
        with open(pdf_filepath, 'w') as f:
            f.write(f"--- Report Type: {report_type} ---\n\n")
            f.write(json_content)
        print(f"Generated placeholder PDF (as TXT): {pdf_filepath}")
    except Exception as e:
        print(f"Error generating placeholder PDF for report {report_id}: {e}")
        pdf_filepath = None

    # Return paths relative to the application root for storage in DB
    # (assuming REPORTS_STORAGE_DIR is at the root or handled by serving mechanism)
    # For consistency, let's make them relative to REPORTS_STORAGE_DIR itself (just filenames)
    # The serving mechanism will prepend REPORTS_STORAGE_DIR.
    # However, the previous implementation returned 'generated_reports/filename.pdf'
    # Let's stick to that for now if FileResponse logic depends on it.
    # If rs.REPORTS_STORAGE_DIR = "generated_reports", then file_path_in_db is "generated_reports/file.pdf"
    # This is fine if the app root is the parent of "generated_reports".

    # To be consistent with how FileResponse might be used (needing path from app root):
    # pdf_file_for_db = os.path.join(os.path.basename(REPORTS_STORAGE_DIR), pdf_filename) if pdf_filepath else None
    # csv_file_for_db = os.path.join(os.path.basename(REPORTS_STORAGE_DIR), csv_filename) if csv_filepath else None
    # For now, just use the full path as it's a placeholder, serving logic needs to be robust.
    # The service stores the path that it knows, FileResponse must construct the actual readable path.
    return pdf_filepath, csv_filepath


# --- Improved Backtesting Logic ---
MIN_OBS_EG_TEST_BACKTEST = 60 # Min observations for reliable Beta for initial part of backtest period

def generate_backtest_data(db: Session, user_id: Optional[int], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates backtesting results for a Z-score based mean-reversion strategy on a pair of tickers.

    Args:
        db: SQLAlchemy database session (currently unused in this simplified version).
        user_id: ID of the user requesting the backtest (for potential future logging or permissioning).
        params: A dictionary of backtesting parameters, expected to include:
            - "tickers" (List[str]): A list of two ticker symbols [Y, X].
            - "start_date" (str): Backtest start date ("YYYY-MM-DD").
            - "end_date" (str): Backtest end date ("YYYY-MM-DD").
            - "z_score_window" (int): Rolling window for Z-score calculation.
            - "entry_z_threshold" (float): Z-score threshold to enter a trade.
            - "exit_z_threshold" (float): Z-score threshold to exit a trade.
            - "strategy_name" (str, optional): Name of the strategy (for metadata).

    Returns:
        A dictionary containing backtest results:
            - "parameters_used": The input parameters.
            - "calculated_hedge_ratio_beta_x": The hedge ratio used.
            - "simulation_period_start"/"end": Actual start/end dates of simulation based on data.
            - "total_pnl_on_spread_units": Total Profit/Loss in terms of spread units.
            - "number_of_trades", "winning_trades", "losing_trades", "win_rate", "average_pnl_per_trade".
            - "sharpe_ratio_approx": Approximate annualized Sharpe Ratio based on daily spread P&L.
            - "equity_curve_dates", "equity_curve_values": Lists for plotting equity curve.
            - "trades_log_sample": A sample of the first few simulated trades.
            - "error" (str, optional): Error message if backtest failed.
            - "traceback" (str, optional): Full traceback if an unhandled exception occurred.
    """
    print(f"Starting backtest generation with params: {params}")

    tickers = params.get("tickers", [])
    if not isinstance(tickers, list) or len(tickers) != 2:
        return {"error": "Backtesting requires a pair of two tickers."}
    ticker_y, ticker_x = tickers[0], tickers[1]

    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    if not start_date_str or not end_date_str:
        return {"error": "Start date and end date are required for backtesting."}

    z_score_window = int(params.get("z_score_window", 20))
    entry_z_threshold = float(params.get("entry_z_threshold", 2.0))
    exit_z_threshold = float(params.get("exit_z_threshold", 0.5))

    try:
        df_y_full = fetch_historical_data(ticker_y, start_date_str, end_date_str)
        df_x_full = fetch_historical_data(ticker_x, start_date_str, end_date_str)

        if df_y_full.empty or 'price' not in df_y_full.columns: return {"error": f"No price data for {ticker_y}."}
        if df_x_full.empty or 'price' not in df_x_full.columns: return {"error": f"No price data for {ticker_x}."}

        series_y_price = df_y_full['price']
        series_x_price = df_x_full['price']

        aligned_df = pd.concat([series_y_price.rename('Y'), series_x_price.rename('X')], axis=1, join='inner').dropna()
        # Ensure enough data for initial beta estimation period + at least one z_score_window period
        if len(aligned_df) < z_score_window + MIN_OBS_EG_TEST_BACKTEST:
            return {"error": f"Overlap data too short ({len(aligned_df)}) for reliable backtest (need {z_score_window + MIN_OBS_EG_TEST_BACKTEST})."}

        s_y = aligned_df['Y']
        s_x = aligned_df['X']

        # Beta calculation segment: Use first MIN_OBS_EG_TEST_BACKTEST points of the *available overlapping data*
        # This is a simplification. A rolling beta or expanding window beta might be more robust.
        beta_calc_series_y = s_y.iloc[:MIN_OBS_EG_TEST_BACKTEST]
        beta_calc_series_x = s_x.iloc[:MIN_OBS_EG_TEST_BACKTEST]

        # Ensure this segment itself has enough data (should be guaranteed by above check if MIN_OBS_EG_TEST_BACKTEST >= COINT_MIN_OBS_EG_TEST)
        if len(beta_calc_series_y) < COINT_MIN_OBS_EG_TEST:
            return {"error": f"Not enough data for initial Beta calculation ({len(beta_calc_series_y)} points, requires {COINT_MIN_OBS_EG_TEST})"}

        eg_test_result = run_engle_granger_test(beta_calc_series_y, beta_calc_series_x)
        if eg_test_result.get("error"): return {"error": f"Hedge ratio calculation failed: {eg_test_result['error']}"}
        beta_x = eg_test_result.get("beta_coefficient")
        if beta_x is None: return {"error": "Could not determine hedge ratio for backtest."}

        spread = calculate_pair_value(s_y, s_x, beta_x=beta_x)
        if spread.empty or len(spread) < z_score_window: return {"error": "Spread series too short or empty after calculation."}

        spread_mean = spread.rolling(window=z_score_window, min_periods=z_score_window).mean()
        spread_std = spread.rolling(window=z_score_window, min_periods=z_score_window).std()

        z_score_series = (spread - spread_mean) / spread_std.replace(0, np.nan) # Avoid division by zero
        z_score_series.replace([np.inf, -np.inf], np.nan, inplace=True) # Handle inf values

        # Align all series for simulation after initial NaNs from rolling calculations are dropped
        sim_df = pd.DataFrame({'price_y': s_y, 'price_x': s_x, 'spread': spread, 'z_score': z_score_series}).dropna()
        if sim_df.empty: return {"error": "No valid data after Z-score calculation (all NaNs)."}

        trades_log = []
        position = 0; entry_spread_price = 0.0; entry_y_price = 0.0; entry_x_price = 0.0
        # Simplified P&L tracking: assumes 1 unit of spread (1 Y vs Beta X)
        # For more realistic P&L, use initial_capital and position sizing.
        daily_pnl_values = [] # Store PnL for each day for Sharpe calc

        for i in range(len(sim_df)):
            current_z = sim_df['z_score'].iloc[i]
            current_spread = sim_df['spread'].iloc[i]
            # current_y_price = sim_df['price_y'].iloc[i] # Not used in this simple P&L
            # current_x_price = sim_df['price_x'].iloc[i]
            current_date = sim_df.index[i]

            daily_pnl = 0.0

            if position == 0: # No position, check for entry
                if current_z < -entry_z_threshold: # Long spread
                    position = 1; entry_spread_price = current_spread
                    trades_log.append({"type": "ENTRY_LONG_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": 0})
                elif current_z > entry_z_threshold: # Short spread
                    position = -1; entry_spread_price = current_spread
                    trades_log.append({"type": "ENTRY_SHORT_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": 0})

            elif position == 1: # Long spread position, check for exit or MTM
                if current_z >= -exit_z_threshold: # Exit condition
                    daily_pnl = current_spread - entry_spread_price
                    trades_log.append({"type": "EXIT_LONG_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": daily_pnl})
                    position = 0
                elif i > 0: # MTM P&L for open position
                     daily_pnl = (current_spread - sim_df['spread'].iloc[i-1]) * position # position is 1

            elif position == -1: # Short spread position, check for exit or MTM
                if current_z <= exit_z_threshold: # Exit condition
                    daily_pnl = entry_spread_price - current_spread
                    trades_log.append({"type": "EXIT_SHORT_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": daily_pnl})
                    position = 0
                elif i > 0: # MTM P&L for open position
                    daily_pnl = (current_spread - sim_df['spread'].iloc[i-1]) * position # position is -1

            daily_pnl_values.append(daily_pnl)

        # If position still open at the end of backtest period, mark to market
        if position != 0 and not sim_df.empty:
            last_spread = sim_df['spread'].iloc[-1]
            last_z = sim_df['z_score'].iloc[-1]
            last_date = sim_df.index[-1]
            eop_pnl = (last_spread - entry_spread_price) * position
            daily_pnl_values[-1] = eop_pnl # Replace last day's MTM with EOP PnL
            trades_log.append({"type": f"CLOSE_EOP_{'LONG' if position==1 else 'SHORT'}", "date": last_date.isoformat(), "spread_price": last_spread, "z_score": last_z, "pnl": eop_pnl})

        daily_pnl_series = pd.Series(daily_pnl_values, index=sim_df.index)
        equity_curve = daily_pnl_series.cumsum()

        closed_trades_pnl = [t['pnl'] for t in trades_log if t['type'].startswith("EXIT_") or t['type'].startswith("CLOSE_EOP_")]
        total_pnl = sum(closed_trades_pnl)
        num_trades = len(closed_trades_pnl)

        sharpe_ratio = (daily_pnl_series.mean() / daily_pnl_series.std()) * np.sqrt(252) if daily_pnl_series.std() != 0 and not daily_pnl_series.empty else 0.0
        if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio): sharpe_ratio = 0.0

        results = {
            "parameters_used": params, "calculated_hedge_ratio_beta_x": beta_x,
            "simulation_period_start": sim_df.index[0].isoformat() if not sim_df.empty else None,
            "simulation_period_end": sim_df.index[-1].isoformat() if not sim_df.empty else None,
            "total_pnl_on_spread_units": round(total_pnl,2), "number_of_trades": num_trades,
            "winning_trades": sum(1 for pnl in closed_trades_pnl if pnl > 0),
            "losing_trades": sum(1 for pnl in closed_trades_pnl if pnl < 0),
            "win_rate": (sum(1 for pnl in closed_trades_pnl if pnl > 0) / num_trades) if num_trades > 0 else 0.0,
            "average_pnl_per_trade": (total_pnl / num_trades) if num_trades > 0 else 0.0,
            "sharpe_ratio_approx": round(sharpe_ratio, 3),
            "equity_curve_dates": equity_curve.index.strftime('%Y-%m-%d').tolist() if not equity_curve.empty else [],
            "equity_curve_values": equity_curve.round(2).tolist() if not equity_curve.empty else [],
            "trades_log_sample": trades_log[:10], # Sample of trades for quick view
        }
        print(f"Backtest for {ticker_y}/{ticker_x} done. P&L: {total_pnl:.2f}, Trades: {num_trades}, Sharpe: {sharpe_ratio:.3f}")
        return results
    except Exception as e:
        import traceback
        error_info = f"Backtest failed for {params.get('tickers')}: {str(e)}"
        print(f"{error_info}
{traceback.format_exc()}")
        return {"error": error_info, "traceback": traceback.format_exc()}

```
