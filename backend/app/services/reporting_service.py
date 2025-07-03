from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
import datetime
import json
import os
import pandas as pd
import numpy as np
from xhtml2pdf import pisa # For PDF generation
from io import BytesIO # For PDF generation in memory before writing

from ..models.models import ReportMetadata, Trade, User
from ..core.config import settings
from .data_collector import fetch_historical_data
from .cointegration_analyzer import run_engle_granger_test, calculate_pair_value, MIN_OBS_FOR_API_EG_TEST as COINT_MIN_OBS_EG_TEST


REPORTS_STORAGE_DIR = getattr(settings, "REPORTS_STORAGE_DIR", "generated_reports")
if not os.path.exists(REPORTS_STORAGE_DIR):
    os.makedirs(REPORTS_STORAGE_DIR, exist_ok=True)

# --- Core Metadata and Summary/Backtest Data Generation Functions (Assumed to be present) ---
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
        if file_path_pdf: db_report.file_path_pdf = file_path_pdf # Should be relative path (filename)
        if file_path_csv: db_report.file_path_csv = file_path_csv # Should be relative path (filename)
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
        "win_rate": (winning_trades / num_trades) if num_trades > 0 else 0.0,
    }

MIN_OBS_EG_TEST_BACKTEST = 60
def generate_backtest_data(db: Session, user_id: Optional[int], params: Dict[str, Any]) -> Dict[str, Any]:
    # ... (Full implementation from previous step) ...
    print(f"Starting backtest generation with params: {params}")
    tickers = params.get("tickers", [])
    if not isinstance(tickers, list) or len(tickers) != 2: return {"error": "Backtesting requires a pair of two tickers."}
    ticker_y, ticker_x = tickers[0], tickers[1]
    start_date_str = params.get("start_date"); end_date_str = params.get("end_date")
    if not start_date_str or not end_date_str: return {"error": "Start date and end date are required."}
    z_score_window = int(params.get("z_score_window", 20))
    entry_z_threshold = float(params.get("entry_z_threshold", 2.0))
    exit_z_threshold = float(params.get("exit_z_threshold", 0.5))
    try:
        df_y_full = fetch_historical_data(ticker_y, start_date_str, end_date_str)
        df_x_full = fetch_historical_data(ticker_x, start_date_str, end_date_str)
        if df_y_full.empty or 'price' not in df_y_full.columns: return {"error": f"No price data for {ticker_y}."}
        if df_x_full.empty or 'price' not in df_x_full.columns: return {"error": f"No price data for {ticker_x}."}
        series_y_price = df_y_full['price']; series_x_price = df_x_full['price']
        aligned_df = pd.concat([series_y_price.rename('Y'), series_x_price.rename('X')], axis=1, join='inner').dropna()
        if len(aligned_df) < z_score_window + MIN_OBS_EG_TEST_BACKTEST: return {"error": f"Overlap data too short ({len(aligned_df)}) for backtest."}
        s_y = aligned_df['Y']; s_x = aligned_df['X']
        beta_calc_series_y = s_y.iloc[:MIN_OBS_EG_TEST_BACKTEST]; beta_calc_series_x = s_x.iloc[:MIN_OBS_EG_TEST_BACKTEST]
        if len(beta_calc_series_y) < COINT_MIN_OBS_EG_TEST: return {"error": f"Not enough data for Beta calc ({len(beta_calc_series_y)})"}
        eg_test_result = run_engle_granger_test(beta_calc_series_y, beta_calc_series_x)
        if eg_test_result.get("error"): return {"error": f"Hedge ratio calc failed: {eg_test_result['error']}"}
        beta_x = eg_test_result.get("beta_coefficient")
        if beta_x is None: return {"error": "Could not determine hedge ratio."}
        spread = calculate_pair_value(s_y, s_x, beta_x=beta_x)
        if spread.empty or len(spread) < z_score_window: return {"error": "Spread insufficient for Z-score."}
        spread_mean = spread.rolling(window=z_score_window, min_periods=z_score_window).mean()
        spread_std = spread.rolling(window=z_score_window, min_periods=z_score_window).std()
        z_score_series = (spread - spread_mean) / spread_std.replace(0, np.nan); z_score_series.replace([np.inf, -np.inf], np.nan, inplace=True)
        sim_df = pd.DataFrame({'price_y': s_y, 'price_x': s_x, 'spread': spread, 'z_score': z_score_series}).dropna()
        if sim_df.empty: return {"error": "No valid data after Z-score calculation."}
        trades_log = []; position = 0; entry_spread_price = 0.0; daily_pnl_values = []
        for i in range(len(sim_df)):
            current_z = sim_df['z_score'].iloc[i]; current_spread = sim_df['spread'].iloc[i]; current_date = sim_df.index[i]; daily_pnl = 0.0
            if position == 0:
                if current_z < -entry_z_threshold: position = 1; entry_spread_price = current_spread; trades_log.append({"type": "ENTRY_LONG_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": 0})
                elif current_z > entry_z_threshold: position = -1; entry_spread_price = current_spread; trades_log.append({"type": "ENTRY_SHORT_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": 0})
            elif position == 1:
                if current_z >= -exit_z_threshold: daily_pnl = current_spread - entry_spread_price; trades_log.append({"type": "EXIT_LONG_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": daily_pnl}); position = 0
                elif i > 0: daily_pnl = (current_spread - sim_df['spread'].iloc[i-1]) * position
            elif position == -1:
                if current_z <= exit_z_threshold: daily_pnl = entry_spread_price - current_spread; trades_log.append({"type": "EXIT_SHORT_SPREAD", "date": current_date.isoformat(), "spread_price": current_spread, "z_score": current_z, "pnl": daily_pnl}); position = 0
                elif i > 0: daily_pnl = (current_spread - sim_df['spread'].iloc[i-1]) * position
            daily_pnl_values.append(daily_pnl)
        if position != 0 and not sim_df.empty:
            last_spread = sim_df['spread'].iloc[-1]; last_z = sim_df['z_score'].iloc[-1]; last_date = sim_df.index[-1]; eop_pnl = (last_spread - entry_spread_price) * position
            daily_pnl_values[-1] = eop_pnl; trades_log.append({"type": f"CLOSE_EOP_{'LONG' if position==1 else 'SHORT'}", "date": last_date.isoformat(), "spread_price": last_spread, "z_score": last_z, "pnl": eop_pnl})
        daily_pnl_series = pd.Series(daily_pnl_values, index=sim_df.index); equity_curve = daily_pnl_series.cumsum()
        closed_trades_pnl = [t['pnl'] for t in trades_log if t['type'].startswith("EXIT_") or t['type'].startswith("CLOSE_EOP_")]
        total_pnl = sum(closed_trades_pnl); num_trades = len(closed_trades_pnl)
        sharpe_ratio = (daily_pnl_series.mean() / daily_pnl_series.std()) * np.sqrt(252) if daily_pnl_series.std() != 0 and not daily_pnl_series.empty else 0.0
        if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio): sharpe_ratio = 0.0
        results = {
            "parameters_used": params, "calculated_hedge_ratio_beta_x": beta_x,
            "simulation_period_start": sim_df.index[0].isoformat() if not sim_df.empty else None, "simulation_period_end": sim_df.index[-1].isoformat() if not sim_df.empty else None,
            "total_pnl_on_spread_units": round(total_pnl,2), "number_of_trades": num_trades,
            "winning_trades": sum(1 for pnl in closed_trades_pnl if pnl > 0), "losing_trades": sum(1 for pnl in closed_trades_pnl if pnl < 0),
            "win_rate": (sum(1 for pnl in closed_trades_pnl if pnl > 0) / num_trades) if num_trades > 0 else 0.0,
            "average_pnl_per_trade": (total_pnl / num_trades) if num_trades > 0 else 0.0,
            "sharpe_ratio_approx": round(sharpe_ratio, 3),
            "equity_curve_dates": equity_curve.index.strftime('%Y-%m-%d').tolist() if not equity_curve.empty else [],
            "equity_curve_values": equity_curve.round(2).tolist() if not equity_curve.empty else [],
            "trades_log_sample": trades_log[:10],
        }
        print(f"Backtest for {tickers[0]}/{tickers[1]} done. P&L: {total_pnl:.2f}, Trades: {num_trades}, Sharpe: {sharpe_ratio:.3f}")
        return results
    except Exception as e:
        import traceback; error_info = f"Backtest failed for {params.get('tickers')}: {str(e)}"; print(f"{error_info}
{traceback.format_exc()}"); return {"error": error_info, "traceback": traceback.format_exc()}


# --- File Generation Logic ---
def _sanitize_for_html(text: Any) -> str:
    """Converts value to string and escapes basic HTML characters."""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def generate_html_for_pdf(report_name: str, report_type: str, data: Dict[str, Any]) -> str:
    """
    Generates an HTML string representation of the report data, suitable for PDF conversion.

    The HTML includes basic styling and sections for:
    - Report title, type, and generation time.
    - Parameters used for the report (if any).
    - Key summary metrics derived from the data.
    - If applicable (e.g., for backtests), sample data for equity curves and trade logs.
    All dynamic data is sanitized to prevent basic HTML injection.

    Args:
        report_name: The user-defined or generated name of the report.
        report_type: The type of report (e.g., "BACKTEST", "DAILY_SUMMARY").
        data: The dictionary containing the core report data, including metrics,
              parameters, and potentially series like equity curves or trade logs.

    Returns:
        A string containing the HTML representation of the report.
    """
    html_report_name = _sanitize_for_html(report_name)
    html_report_type = _sanitize_for_html(report_type)

    styles = """
    <style type="text/css">
        @page { size: a4 portrait; margin: 1cm; }
        body { font-family: "Helvetica", "Arial", sans-serif; margin: 0; font-size: 10pt; color: #333; }
        h1 { font-size: 18pt; color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 6px; margin-bottom: 15px;}
        h2 { font-size: 14pt; color: #283593; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #9fa8da; padding-bottom: 4px;}
        p { line-height: 1.4; margin-bottom: 10px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; margin-bottom: 20px; font-size: 9pt; }
        th, td { border: 1px solid #cccccc; padding: 8px; text-align: left; }
        th { background-color: #e8eaf6; font-weight: bold; color: #1a237e;}
        tr:nth-child(even) { background-color: #f9f9f9; }
        pre { background-color: #f0f0f0; border: 1px solid #dddddd; padding: 10px; white-space: pre-wrap; word-wrap: break-word; font-size: 8pt; margin-top: 5px; }
        .metrics-table td:first-child { font-weight: bold; width: 40%; background-color: #f5f5f5; }
        .page-break { page-break-before: always; }
        .header-info { margin-bottom: 20px; font-size: 9pt; color: #555; }
        .header-info p { margin: 2px 0; }
    </style>
    """
    html_content = f"<html><head><meta charset='UTF-8'><title>{html_report_name}</title>{styles}</head><body>"
    html_content += f"<h1>Report: {html_report_name}</h1>"
    html_content += f"<div class='header-info'><p><strong>Type:</strong> {html_report_type}</p>"
    html_content += f"<p><strong>Generated At:</strong> {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p></div>"

    parameters = data.get("parameters_used", data.get("parameters")) # Check both for flexibility
    if isinstance(parameters, dict) and parameters:
        html_content += "<h2>Parameters Used</h2><table class='metrics-table'>"
        for key, value in parameters.items():
            html_content += f"<tr><td>{_sanitize_for_html(key).replace('_', ' ').title()}</td><td>{_sanitize_for_html(value)}</td></tr>"
        html_content += "</table>"

    # Isolate simple metrics (non-list/dict) for summary table
    simple_metrics = { k: v for k, v in data.items() if not isinstance(v, (list, dict)) or k == "calculated_hedge_ratio_beta_x"}
    # Remove known complex fields that might have been missed if not list/dict (e.g. if parameters was a string)
    for complex_key in ["parameters_used", "parameters", "trades_log_sample", "equity_curve_dates", "equity_curve_values"]:
        if complex_key in simple_metrics: del simple_metrics[complex_key]

    if simple_metrics:
        html_content += "<h2>Summary Metrics</h2><table class='metrics-table'>"
        for key, value in simple_metrics.items():
            v_str = f"{value:.4f}" if isinstance(value, (float, np.floating)) and pd.notnull(value) else _sanitize_for_html(value)
            html_content += f"<tr><td>{_sanitize_for_html(key).replace('_', ' ').title()}</td><td>{v_str}</td></tr>"
        html_content += "</table>"

    if data.get("equity_curve_dates") and data.get("equity_curve_values"):
        html_content += "<h2 class='page-break'>Equity Curve Data</h2><p>Note: A visual chart is available in the web UI. This table shows a sample of equity points.</p><table><tr><th>Date</th><th>Equity Value</th></tr>"
        dates, values = data["equity_curve_dates"], data["equity_curve_values"]
        # Sample data if too long for PDF
        sample_size = 20
        display_data = list(zip(dates, values))
        if len(display_data) > sample_size:
            # Display first N, middle N/2, last N (approx)
            # This is a more complex sampling, for now, just take first and last `sample_size` points if too long
            display_data = display_data[:sample_size//2] + display_data[-sample_size//2:]
            html_content += "<p><em>(Data sampled for brevity in PDF)</em></p>"

        for date_val, equity_val in display_data:
            html_content += f"<tr><td>{_sanitize_for_html(date_val)}</td><td>{equity_val:.2f}</td></tr>"
        html_content += "</table>"

    trades_log_sample = data.get("trades_log_sample")
    if isinstance(trades_log_sample, list) and trades_log_sample:
        html_content += "<h2 class='page-break'>Sample Trades Log</h2><table><tr>"
        headers = trades_log_sample[0].keys()
        for header in headers: html_content += f"<th>{_sanitize_for_html(header).replace('_', ' ').title()}</th>"
        html_content += "</tr>"
        for trade_idx, trade in enumerate(trades_log_sample):
            if trade_idx >= 10: # Limit sample size in PDF
                 html_content += "<tr><td colspan='" + str(len(headers)) + "'>... (log truncated in PDF) ...</td></tr>"; break
            html_content += "<tr>"
            for header in headers:
                val = trade.get(header)
                val_str = f"{val:.4f}" if isinstance(val, (float, np.floating)) and pd.notnull(val) else _sanitize_for_html(val)
                html_content += f"<td>{val_str}</td>"
            html_content += "</tr>"
        html_content += "</table>"

    html_content += "</body></html>"
    return html_content


def generate_report_files(report_id: int, report_name: str, data: Dict[str, Any], report_type: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Generates CSV and PDF report files from the provided data.
    Generates and saves CSV and PDF report files based on the provided data.

    - CSV files are structured to include a header with report metadata (name, type, ID,
      generation time, parameters), followed by sections for summary metrics,
      equity curve data (if applicable), and a trades log (if applicable). Pandas
      is used for CSV creation to ensure proper formatting.
    - PDF files are generated by converting an HTML summary (created by the
      `generate_html_for_pdf` helper function) to PDF using the `xhtml2pdf` library.

    Files are saved into the directory specified by `settings.REPORTS_STORAGE_DIR`.
    If PDF generation encounters an error, a debug HTML file (`_debug.html`) containing
    the problematic HTML content is saved to aid in troubleshooting.

    Args:
        report_id: The unique ID of the report, used in filenames.
        report_name: The name of the report, used in filenames and as the HTML title.
        data: The core data dictionary for the report, containing all metrics, parameters,
              and series (like equity curves or trade logs) to be included.
        report_type: The type of report (e.g., "BACKTEST", "DAILY_SUMMARY"), used in
                     the HTML title and CSV header.

    Returns:
        A tuple `(pdf_filename_relative, csv_filename_relative)`. Each element is the
        relative filename (e.g., "my_report_123.pdf") if generation was successful for that
        format, or `None` if it failed. These relative filenames are intended to be stored
        in the `ReportMetadata` database record.
    """
    # Sanitize report_name for use in filename, remove problematic characters
    safe_report_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in report_name).rstrip().replace(' ', '_')
    base_filename = f"{safe_report_name}_{report_id}"

    pdf_filename_rel, csv_filename_rel = None, None

    # --- CSV Generation ---
    csv_filename = f"{base_filename}.csv"
    csv_filepath_abs = os.path.join(REPORTS_STORAGE_DIR, csv_filename)
    try:
        # Create a comprehensive header for the CSV
        csv_header_lines = [
            f"# Report Name: {report_name}",
            f"# Report Type: {report_type}",
            f"# Report ID: {report_id}",
            f"# Generated At: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
            "#"
        ]
        parameters = data.get("parameters_used", data.get("parameters"))
        if isinstance(parameters, dict) and parameters:
            csv_header_lines.append("# Parameters Used:")
            for pk, pv in parameters.items(): csv_header_lines.append(f"#   {pk}: {pv}")
            csv_header_lines.append("#")

        with open(csv_filepath_abs, 'w', newline='') as f:
            f.write("\n".join(csv_header_lines) + "\n\n")

            # Main summary metrics
            main_metrics_data = { k: v for k, v in data.items() if not isinstance(v, (list, dict)) or k == "calculated_hedge_ratio_beta_x"}
            # remove parameter keys if they were flattened into data
            for pk in (parameters.keys() if isinstance(parameters, dict) else []):
                if f"param_{pk}" in main_metrics_data: del main_metrics_data[f"param_{pk}"]
            if "parameters_used" in main_metrics_data: del main_metrics_data["parameters_used"]
            if "parameters" in main_metrics_data: del main_metrics_data["parameters"]


            if main_metrics_data:
                df_main_metrics = pd.Series(main_metrics_data).to_frame("Value"); df_main_metrics.index.name = "Metric"
                f.write("## Summary Metrics\n")
                df_main_metrics.to_csv(f, header=True); f.write("\n\n")

            # Equity Curve Data
            if data.get("equity_curve_dates") and data.get("equity_curve_values"):
                df_equity = pd.DataFrame({"date": data["equity_curve_dates"], "equity_value": data["equity_curve_values"]})
                f.write("## Equity Curve Data\n"); df_equity.to_csv(f, index=False, header=True); f.write("\n\n")

            # Trades Log (full log if available, not just sample)
            trades_log = data.get("trades_log", data.get("trades_log_sample")) # Prefer full log if exists
            if isinstance(trades_log, list) and trades_log:
                df_trades = pd.DataFrame(trades_log)
                f.write("## Trades Log\n"); df_trades.to_csv(f, index=False, header=True); f.write("\n\n")

        csv_filename_rel = csv_filename # Store just filename
        print(f"Generated CSV report: {csv_filepath_abs}")
    except Exception as e:
        print(f"Error generating CSV for '{report_name}': {e}")
        # import traceback; traceback.print_exc() # For detailed debug

    # --- PDF Generation ---
    pdf_filename = f"{base_filename}.pdf"
    pdf_filepath_abs = os.path.join(REPORTS_STORAGE_DIR, pdf_filename)
    try:
        html_content = generate_html_for_pdf(report_name, report_type, data)

        with open(pdf_filepath_abs, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(BytesIO(html_content.encode('UTF-8')), dest=pdf_file, encoding='UTF-8')

        if not pisa_status.err:
            pdf_filename_rel = pdf_filename # Store just filename
            print(f"Generated PDF report: {pdf_filepath_abs}")
        else:
            print(f"Error generating PDF for '{report_name}': {pisa_status.err}")
            debug_html_path = os.path.join(REPORTS_STORAGE_DIR, f"{base_filename}_debug.html")
            with open(debug_html_path, "w", encoding="utf-8") as f_html:
                f_html.write(html_content)
            print(f"Saved HTML content for PDF debugging: {debug_html_path}")
    except Exception as e:
        print(f"Critical error during PDF generation for '{report_name}': {e}")
        # import traceback; traceback.print_exc()

    return pdf_filename_rel, csv_filename_rel

```
