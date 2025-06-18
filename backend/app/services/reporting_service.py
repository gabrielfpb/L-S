from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
import datetime
import json # For serializing complex data into JSONB if needed
import os # For file paths
import numpy as np # For placeholder backtest data

from ..models.models import ReportMetadata, Trade, User
from ..core.config import settings # For report storage path if defined

# Placeholder for report storage directory (ideally from settings)
REPORTS_STORAGE_DIR = getattr(settings, "REPORTS_STORAGE_DIR", "generated_reports")
os.makedirs(REPORTS_STORAGE_DIR, exist_ok=True)


def create_report_metadata_entry(
    db: Session,
    report_type: str,
    user_id: Optional[int] = None,
    parameters: Optional[Dict[str, Any]] = None,
    celery_task_id: Optional[str] = None,
    report_name: Optional[str] = None
) -> ReportMetadata:
    if not report_name:
        report_name = f"{report_type.lower().replace('_', '-')}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}"

    db_report = ReportMetadata(
        report_name=report_name,
        report_type=report_type,
        user_id=user_id,
        parameters=parameters,
        status="PENDING", # Initial status
        celery_task_id=celery_task_id
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def update_report_status(
    db: Session,
    report_id: int,
    status: str,
    error_message: Optional[str] = None,
    summary_data: Optional[Dict[str, Any]] = None,
    file_path_pdf: Optional[str] = None,
    file_path_csv: Optional[str] = None,
    generation_started_at: Optional[datetime.datetime] = None,
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

        db.commit()
        db.refresh(db_report)
    return db_report

def get_report_metadata_by_id(db: Session, report_id: int) -> Optional[ReportMetadata]:
    return db.query(ReportMetadata).filter(ReportMetadata.id == report_id).first()

def list_reports_metadata(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ReportMetadata]:
    query = db.query(ReportMetadata)
    if user_id: # Filter by user if ID provided
        query = query.filter(ReportMetadata.user_id == user_id)
    return query.order_by(ReportMetadata.generation_requested_at.desc()).offset(skip).limit(limit).all()


# --- Actual Report Generation Logic (Placeholders/Simplified) ---

def generate_performance_summary_data(db: Session, user_id: Optional[int], period: str = "DAILY") -> Dict[str, Any]:
    """
    Generates data for a performance summary report.
    Placeholder: Calculates total P&L from closed trades for the user in a given period.
    """
    end_date = datetime.datetime.now(datetime.timezone.utc)
    if period.upper() == "DAILY":
        start_date = end_date - datetime.timedelta(days=1)
    elif period.upper() == "WEEKLY":
        start_date = end_date - datetime.timedelta(weeks=1)
    else:
        start_date = end_date - datetime.timedelta(days=1) # Default to daily

    query = db.query(Trade).filter(Trade.status == "CLOSED", Trade.exit_datetime >= start_date, Trade.exit_datetime <= end_date)
    if user_id:
        query = query.filter(Trade.user_id == user_id)

    closed_trades = query.all()

    total_pnl = sum(trade.realized_pnl for trade in closed_trades if trade.realized_pnl is not None)
    num_trades = len(closed_trades)
    winning_trades = sum(1 for trade in closed_trades if trade.realized_pnl is not None and trade.realized_pnl > 0)
    losing_trades = sum(1 for trade in closed_trades if trade.realized_pnl is not None and trade.realized_pnl < 0)

    summary = {
        "period": period.upper(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "user_id": user_id if user_id else "All Users",
        "total_pnl": total_pnl,
        "number_of_trades_closed": num_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": (winning_trades / num_trades) if num_trades > 0 else 0,
    }
    return summary

def generate_backtest_data(db: Session, user_id: Optional[int], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates data for a backtest report. Extremely simplified placeholder.
    """
    backtest_results = {
        "strategy_used": params.get("strategy_name", "N/A"),
        "parameters": params,
        "simulated_final_pnl": np.random.uniform(-5000, 15000),
        "simulated_sharpe_ratio": np.random.uniform(0.1, 1.5),
        "simulated_num_trades": np.random.randint(5, 50),
        "message": "This is a placeholder backtest result. Actual logic not implemented.",
        "data_points_processed": np.random.randint(200,1000)
    }
    return backtest_results

# --- File Generation (Placeholders) ---
def generate_report_files(report_id: int, report_name: str, data: Dict[str, Any], report_type: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Placeholder for generating PDF and CSV files. Saves a JSON representation for now.
    Returns (relative_pdf_path, relative_csv_path)
    """
    base_filename = f"{report_name.replace(' ', '_').replace(':', '')}_{report_id}" # Sanitize name

    json_content = json.dumps(data, indent=4, default=str)

    csv_filename = f"{base_filename}.csv"
    csv_filepath = os.path.join(REPORTS_STORAGE_DIR, csv_filename)
    try:
        with open(csv_filepath, 'w') as f:
            if isinstance(data, dict) and data: # Simplified CSV
                f.write(",".join(map(str, data.keys())) + "\n")
                f.write(",".join(map(str, data.values())) + "\n")
            else:
                f.write(json_content)
        print(f"Generated placeholder CSV: {csv_filepath}")
    except Exception as e:
        print(f"Error generating placeholder CSV for report {report_id}: {e}")
        csv_filepath = None

    pdf_filename = f"{base_filename}.pdf.txt" # Save as .txt
    pdf_filepath = os.path.join(REPORTS_STORAGE_DIR, pdf_filename)
    try:
        with open(pdf_filepath, 'w') as f:
            f.write(f"--- Report Type: {report_type} ---\n\n")
            f.write(json_content)
        print(f"Generated placeholder PDF (as TXT): {pdf_filepath}")
    except Exception as e:
        print(f"Error generating placeholder PDF for report {report_id}: {e}")
        pdf_filepath = None

    # Return relative paths from the application's perspective for storage in DB
    # The serving mechanism will need to know the absolute base path (REPORTS_STORAGE_DIR)
    relative_pdf_path = os.path.join(os.path.basename(REPORTS_STORAGE_DIR), pdf_filename) if pdf_filepath else None
    relative_csv_path = os.path.join(os.path.basename(REPORTS_STORAGE_DIR), csv_filename) if csv_filepath else None

    return relative_pdf_path, relative_csv_path
