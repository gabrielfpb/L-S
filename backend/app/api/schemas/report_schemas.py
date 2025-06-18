from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import datetime
import os # For path manipulation in validator if needed

class ReportMetadataBase(BaseModel):
    report_name: Optional[str] = None
    report_type: str
    user_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None

class ReportMetadataResponse(ReportMetadataBase):
    id: int
    generation_requested_at: datetime.datetime
    generation_started_at: Optional[datetime.datetime] = None
    generation_completed_at: Optional[datetime.datetime] = None
    status: str
    summary_data: Optional[Dict[str, Any]] = None # Could be more specific if summary structure is known
    error_message: Optional[str] = None
    file_path_pdf: Optional[str] = None # Relative path from REPORTS_STORAGE_DIR
    file_path_csv: Optional[str] = None # Relative path
    celery_task_id: Optional[str] = None

    download_url_pdf: Optional[str] = None
    download_url_csv: Optional[str] = None

    class Config:
        orm_mode = True

    # Validators to construct download URLs dynamically
    # These assume that the API serves files from /api/v1/reports/{report_id}/download/{format}
    @validator('download_url_pdf', always=True)
    def assemble_pdf_url(cls, v, values):
        if values.get('file_path_pdf') and values.get('status') == "COMPLETED":
            return f"/api/v1/reports/{values['id']}/download/pdf"
        return None

    @validator('download_url_csv', always=True)
    def assemble_csv_url(cls, v, values):
        if values.get('file_path_csv') and values.get('status') == "COMPLETED":
            return f"/api/v1/reports/{values['id']}/download/csv"
        return None


class GenerateSummaryReportRequestSchema(BaseModel):
    report_type: str = Field(..., description="Type of summary report, e.g., DAILY, WEEKLY")
    report_name: Optional[str] = None


class GenerateBacktestReportRequestSchema(BaseModel):
    report_name: Optional[str] = None
    strategy_name: str = Field(default="default_zscore_pair_trading", description="Identifier for the backtesting strategy")
    tickers: List[str] = Field(..., min_length=1, description="List of tickers. For pairs, typically [Y, X].")
    start_date: datetime.date # Using datetime.date for date inputs
    end_date: datetime.date
    initial_capital: Optional[float] = Field(default=100000.0, gt=0)
    # Add other strategy-specific parameters here, e.g.:
    # zscore_threshold: Optional[float] = Field(default=2.0)
    # window1: Optional[int] = Field(default=20)
    # window2: Optional[int] = Field(default=60)


class ReportGenerationResponse(BaseModel):
    message: str
    report_id: int
    task_id: str
    status_check_url: str # URL to check Celery task status (e.g., /api/v1/tasks/status/{task_id})
