from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import os

from ...core.database import get_db
from ...services import reporting_service as rs
from ...tasks.report_tasks import task_generate_summary_report, task_generate_backtest_report
from ..schemas.report_schemas import (
    ReportMetadataResponse, GenerateSummaryReportRequestSchema,
    GenerateBacktestReportRequestSchema, ReportGenerationResponse
)
from ..dependencies import get_current_active_user
from ...models.models import User as UserModel
from ...core.config import settings # Import settings for REPORTS_STORAGE_DIR

from fastapi.responses import FileResponse

router = APIRouter()

@router.post("/generate_summary", response_model=ReportGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_summary_report_endpoint(
    request_data: GenerateSummaryReportRequestSchema,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    report_entry = rs.create_report_metadata_entry(
        db, report_type=request_data.report_type.upper() + "_SUMMARY",
        user_id=current_user.id,
        report_name=request_data.report_name,
        parameters={"period": request_data.report_type}
    )
    task = task_generate_summary_report.delay(
        report_id=report_entry.id,
        user_id=current_user.id,
        period=request_data.report_type.upper()
    )
    report_entry.celery_task_id = task.id
    db.commit()
    return ReportGenerationResponse(
        message="Summary report generation has been queued.",
        report_id=report_entry.id,
        task_id=task.id,
        status_check_url=f"/api/v1/tasks/status/{task.id}"
    )

@router.post("/generate_backtest", response_model=ReportGenerationResponse, status_code=status.HTTP_202_ACCEPTED,
             summary="Queue Backtest Report Generation",
             description="Queues a Celery task to generate a backtest report for a specified strategy and asset pair(s). "
                         "Requires tickers, date range, and strategy parameters like Z-score window and thresholds. "
                         "Returns a task ID for status tracking and the ID of the created report metadata entry.")
async def generate_backtest_report_endpoint( # This function name was correct, but the route path above was wrong in previous diff
    request_data: GenerateBacktestReportRequestSchema,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    params_for_report = request_data.dict()
    report_entry = rs.create_report_metadata_entry(
        db, report_type="BACKTEST",
        user_id=current_user.id,
        report_name=request_data.report_name,
        parameters=params_for_report
    )
    task = task_generate_backtest_report.delay(
        report_id=report_entry.id,
        user_id=current_user.id,
        backtest_params=params_for_report
    )
    report_entry.celery_task_id = task.id
    db.commit()
    return ReportGenerationResponse(
        message="Backtest report generation has been queued.",
        report_id=report_entry.id,
        task_id=task.id,
        status_check_url=f"/api/v1/tasks/status/{task.id}"
    )

@router.get("/", response_model=List[ReportMetadataResponse])
async def list_all_reports(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    user_id_to_filter = current_user.id if not current_user.is_superuser else None
    reports_db = rs.list_reports_metadata(db, user_id=user_id_to_filter, skip=skip, limit=limit)

    # Pydantic models with validators handle dynamic URL creation
    return [ReportMetadataResponse.from_orm(report) for report in reports_db]


@router.get("/{report_id}", response_model=ReportMetadataResponse)
async def get_specific_report_metadata(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    report = rs.get_report_metadata_by_id(db, report_id=report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not current_user.is_superuser and report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this report")

    return ReportMetadataResponse.from_orm(report)


@router.get("/{report_id}/download/{file_format}", response_class=FileResponse)
async def download_report_file(
    report_id: int,
    file_format: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    report = rs.get_report_metadata_by_id(db, report_id=report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report metadata not found")
    if not current_user.is_superuser and report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to download this report")
    if report.status != "COMPLETED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Report is not yet completed. Current status: {report.status}")

    file_path_in_db = None
    if file_format.lower() == "pdf":
        file_path_in_db = report.file_path_pdf
    elif file_format.lower() == "csv":
        file_path_in_db = report.file_path_csv
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file format requested. Use 'pdf' or 'csv'.")

    if not file_path_in_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{file_format.upper()} file not available for this report.")

    # Construct absolute path from stored relative path
    # REPORTS_STORAGE_DIR is the base directory where generated_reports (or similar) folder resides.
    # file_path_in_db should be like 'generated_reports/filename.pdf'
    # So, we need the parent of REPORTS_STORAGE_DIR to join with file_path_in_db
    # Or, more simply, ensure file_path_in_db is relative to REPORTS_STORAGE_DIR base.
    # For now, assume file_path_in_db is relative *within* REPORTS_STORAGE_DIR or an absolute path.
    # If file_path_in_db is 'filename.pdf', then:
    # full_file_path = os.path.join(rs.REPORTS_STORAGE_DIR, file_path_in_db)
    # If file_path_in_db is 'generated_reports/filename.pdf' and REPORTS_STORAGE_DIR is '.../generated_reports'
    # we need to be careful. The service stores relative path from *inside* REPORTS_STORAGE_DIR if I recall.
    # Let's assume file_path_in_db is just the filename, and it's inside rs.REPORTS_STORAGE_DIR

    # The reporting_service.generate_report_files returns path like 'generated_reports/file.csv'
    # If rs.REPORTS_STORAGE_DIR is '/app/generated_reports', then the path stored is 'generated_reports/file.csv'
    # This means the path is relative to the project root if the service is consistent.
    # For FileResponse, we need an absolute path or path relative to where FastAPI is run.
    # The `file_path_in_db` should store just the filename, e.g., "my_report_123.pdf"
    # as returned by reporting_service.generate_report_files
    # The absolute path is constructed using settings.REPORTS_STORAGE_DIR
    absolute_file_path = os.path.join(settings.REPORTS_STORAGE_DIR, file_path_in_db)

    if not os.path.isfile(absolute_file_path): # Use os.path.isfile for a more specific check
        print(f"File not found on server: {absolute_file_path} (linked from report ID {report_id})")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The requested {file_format.upper()} file was not found on the server.")

    # filename for FileResponse should be the actual name of the file being served,
    # which is what the user will see as the download name.
    return FileResponse(path=absolute_file_path, filename=file_path_in_db, media_type=media_type)
