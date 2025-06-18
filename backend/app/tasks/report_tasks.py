from celery import shared_task
import datetime
from typing import Optional, Dict, Any # Added Optional, Dict, Any

from ..core.database import SessionLocal # To create DB session within task
from ..services import reporting_service as rs
# from ..services.email_service import send_report_email # If email service exists

@shared_task(name="tasks.generate_summary_report_task", bind=True)
def task_generate_summary_report(self, report_id: int, user_id: Optional[int], period: str):
    """ Celery task to generate a summary report. """
    db = SessionLocal()
    try:
        print(f"Task started: Generate Summary Report ID {report_id} for period {period}")
        rs.update_report_status(db, report_id=report_id, status="PROCESSING", generation_started_at=datetime.datetime.now(datetime.timezone.utc))

        summary_data = rs.generate_performance_summary_data(db, user_id=user_id, period=period)

        db_report = rs.get_report_metadata_by_id(db, report_id)
        if not db_report:
            raise Exception(f"ReportMetadata entry {report_id} not found.")

        pdf_path, csv_path = rs.generate_report_files(
            report_id=report_id,
            report_name=db_report.report_name or f"summary_{period.lower()}_{report_id}",
            data=summary_data,
            report_type=f"{period.upper()}_SUMMARY"
        )

        rs.update_report_status(
            db, report_id=report_id, status="COMPLETED",
            summary_data=summary_data, file_path_pdf=pdf_path, file_path_csv=csv_path,
            generation_completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        print(f"Task completed: Summary Report ID {report_id}")
        # send_report_email(user_email, report_id, pdf_path) # Optional
        return {"report_id": report_id, "status": "COMPLETED", "pdf_path": pdf_path, "csv_path": csv_path}
    except Exception as e:
        print(f"Task failed: Summary Report ID {report_id}. Error: {e}")
        rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=str(e), generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
        raise
    finally:
        db.close()


@shared_task(name="tasks.generate_backtest_report_task", bind=True)
def task_generate_backtest_report(self, report_id: int, user_id: Optional[int], backtest_params: Dict[str, Any]):
    """ Celery task to generate a backtest report. """
    db = SessionLocal()
    try:
        print(f"Task started: Generate Backtest Report ID {report_id} with params {backtest_params}")
        rs.update_report_status(db, report_id=report_id, status="PROCESSING", generation_started_at=datetime.datetime.now(datetime.timezone.utc))

        backtest_data = rs.generate_backtest_data(db, user_id=user_id, params=backtest_params)

        db_report = rs.get_report_metadata_by_id(db, report_id)
        if not db_report:
            raise Exception(f"ReportMetadata entry {report_id} not found.")

        pdf_path, csv_path = rs.generate_report_files(
            report_id=report_id,
            report_name=db_report.report_name or f"backtest_{backtest_params.get('strategy_name','default')}_{report_id}",
            data=backtest_data,
            report_type="BACKTEST"
        )

        rs.update_report_status(
            db, report_id=report_id, status="COMPLETED",
            summary_data=backtest_data,
            file_path_pdf=pdf_path, file_path_csv=csv_path,
            generation_completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        print(f"Task completed: Backtest Report ID {report_id}")
        return {"report_id": report_id, "status": "COMPLETED", "pdf_path": pdf_path, "csv_path": csv_path}
    except Exception as e:
        print(f"Task failed: Backtest Report ID {report_id}. Error: {e}")
        rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=str(e), generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
        raise
    finally:
        db.close()
