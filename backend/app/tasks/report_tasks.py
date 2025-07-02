from celery import shared_task
import datetime
from typing import Optional, Dict, Any # Ensure these are imported

from ..core.database import SessionLocal
from ..services import reporting_service as rs
# from ..services.email_service import send_report_email # If email service exists

@shared_task(name="tasks.generate_summary_report_task", bind=True)
def task_generate_summary_report(self, report_id: int, user_id: Optional[int], period: str):
    db = SessionLocal()
    try:
        print(f"Task started: Generate Summary Report ID {report_id} for period {period}")
        rs.update_report_status(db, report_id=report_id, status="PROCESSING", generation_started_at=datetime.datetime.now(datetime.timezone.utc))

        summary_data_result = rs.generate_performance_summary_data(db, user_id=user_id, period=period)

        # Check if the service function itself returned an error
        if isinstance(summary_data_result, dict) and "error" in summary_data_result:
            error_msg = f"Data generation failed: {summary_data_result['error']}"
            print(f"Task error (from service): Summary Report ID {report_id}. Error: {error_msg}")
            rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=error_msg, generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
            # Raise an exception to ensure Celery also marks the task as failed
            raise Exception(error_msg)

        db_report = rs.get_report_metadata_by_id(db, report_id)
        if not db_report:
            # This case should ideally not happen if report_id is valid
            raise Exception(f"ReportMetadata entry {report_id} not found after data generation.")

        pdf_path, csv_path = rs.generate_report_files(
            report_id=report_id,
            report_name=db_report.report_name or f"summary_{period.lower()}_{report_id}",
            data=summary_data_result, # Use the result directly
            report_type=f"{period.upper()}_SUMMARY"
        )

        rs.update_report_status(
            db, report_id=report_id, status="COMPLETED",
            summary_data=summary_data_result, file_path_pdf=pdf_path, file_path_csv=csv_path,
            generation_completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        print(f"Task completed: Summary Report ID {report_id}")
        return {"report_id": report_id, "status": "COMPLETED", "pdf_path": pdf_path, "csv_path": csv_path}
    except Exception as e:
        # This block catches exceptions from generate_report_files, get_report_metadata_by_id,
        # or the explicit raise Exception(error_msg) above, or any other unexpected error.
        error_message_for_db = str(e)
        print(f"Task failed: Summary Report ID {report_id}. Error: {error_message_for_db}")
        # Ensure status is updated even if it was already set to FAILED by the service error check
        # Also ensure generation_completed_at is set for FAILED tasks.
        rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=error_message_for_db, generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
        # Re-raise so Celery's machinery knows the task failed.
        # self.update_state(state='FAILURE', meta={'exc': str(e)}) # Alternative for custom state details
        raise
    finally:
        db.close()


@shared_task(name="tasks.generate_backtest_report_task", bind=True)
def task_generate_backtest_report(self, report_id: int, user_id: Optional[int], backtest_params: Dict[str, Any]):
    db = SessionLocal()
    try:
        print(f"Task started: Generate Backtest Report ID {report_id} with params {backtest_params}")
        rs.update_report_status(db, report_id=report_id, status="PROCESSING", generation_started_at=datetime.datetime.now(datetime.timezone.utc))

        backtest_data_result = rs.generate_backtest_data(db, user_id=user_id, params=backtest_params)

        # Check if the service function itself returned an error
        if isinstance(backtest_data_result, dict) and "error" in backtest_data_result:
            error_msg = f"Backtest data generation failed: {backtest_data_result['error']}"
            print(f"Task error (from service): Backtest Report ID {report_id}. Error: {error_msg}")
            rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=error_msg, generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
            raise Exception(error_msg)

        db_report = rs.get_report_metadata_by_id(db, report_id)
        if not db_report:
            raise Exception(f"ReportMetadata entry {report_id} not found after data generation.")

        pdf_path, csv_path = rs.generate_report_files(
            report_id=report_id,
            report_name=db_report.report_name or f"backtest_{backtest_params.get('strategy_name','default')}_{report_id}",
            data=backtest_data_result,
            report_type="BACKTEST"
        )

        rs.update_report_status(
            db, report_id=report_id, status="COMPLETED",
            summary_data=backtest_data_result,
            file_path_pdf=pdf_path, file_path_csv=csv_path,
            generation_completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        print(f"Task completed: Backtest Report ID {report_id}")
        return {"report_id": report_id, "status": "COMPLETED", "pdf_path": pdf_path, "csv_path": csv_path}
    except Exception as e:
        error_message_for_db = str(e)
        print(f"Task failed: Backtest Report ID {report_id}. Error: {error_message_for_db}")
        # Also ensure generation_completed_at is set for FAILED tasks.
        rs.update_report_status(db, report_id=report_id, status="FAILED", error_message=error_message_for_db, generation_completed_at=datetime.datetime.now(datetime.timezone.utc))
        raise
    finally:
        db.close()
```
