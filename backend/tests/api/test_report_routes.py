import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock, ANY # Import ANY
import os
import tempfile
import shutil # For cleaning up temp_reports_dir_module if needed

from app.models.models import ReportMetadata, User # Assuming User might be used by authenticated_client
from app.core.config import settings

# Assuming conftest.py provides authenticated_client and db (SQLAlchemy session) fixtures

@pytest.fixture(scope="module") # Use "module" scope for efficiency if dir is shared by multiple tests in this file
def temp_reports_dir_module(tmp_path_factory):
    # Create a temporary directory for storing test report files for this test module
    temp_dir = tmp_path_factory.mktemp("test_reports_module_scope")
    print(f"Created temp reports dir for module: {temp_dir}")
    yield str(temp_dir) # Provide the path as a string
    # print(f"Cleaning up temp reports dir for module: {temp_dir}")
    # shutil.rmtree(temp_dir) # Cleanup if needed, but tmp_path_factory usually handles it

@pytest.fixture
def mock_report_service_get_metadata(monkeypatch):
    mock_get = MagicMock()
    # This mock will be configured per test for the specific report metadata needed
    monkeypatch.setattr("app.api.routes.report_routes.rs.get_report_metadata_by_id", mock_get)
    return mock_get

# This fixture depends on authenticated_client which itself depends on db session
def setup_test_report_file(
    tmp_dir: str, report_id: int, user_id_for_auth: int,
    file_format: str, filename_in_db: str, content: bytes
):
    file_path = os.path.join(tmp_dir, filename_in_db)
    with open(file_path, "wb") as f:
        f.write(content)

    mock_meta = MagicMock(spec=ReportMetadata)
    mock_meta.id = report_id
    mock_meta.user_id = user_id_for_auth
    mock_meta.status = "COMPLETED"
    mock_meta.file_path_pdf = filename_in_db if file_format == "pdf" else None
    mock_meta.file_path_csv = filename_in_db if file_format == "csv" else None
    return mock_meta


def test_download_report_file_pdf_success(
    authenticated_client: TestClient, # From conftest.py, provides auth and user context
    mock_report_service_get_metadata: MagicMock,
    temp_reports_dir_module: str, # Use the module-scoped temp dir
    monkeypatch,
    db: Session # To get current user from auth client if needed, or assume ID 1
):
    # 1. Monkeypatch REPORTS_STORAGE_DIR to use the temp directory
    monkeypatch.setattr(settings, "REPORTS_STORAGE_DIR", temp_reports_dir_module)

    # 2. Setup: Create a dummy PDF file and mock metadata
    report_id = 1
    # Assuming test user from authenticated_client has ID 1.
    # This needs to align with how authenticated_client creates/retrieves its user.
    # For robustness, one might fetch the user ID from the token if possible, or have fixture return it.
    # For now, assuming user_id=1 from conftest.py's authenticated_client.
    test_user_id = 1 # Placeholder if user ID cannot be easily extracted from client

    pdf_filename = f"test_report_{report_id}.pdf"
    pdf_content = b"%PDF-1.4 fake PDF content for test"

    mock_metadata = setup_test_report_file(
        temp_reports_dir_module, report_id, test_user_id, "pdf", pdf_filename, pdf_content
    )
    mock_report_service_get_metadata.return_value = mock_metadata

    response = authenticated_client.get(f"/api/v1/reports/{report_id}/download/pdf")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="{pdf_filename}"'
    assert response.content == pdf_content
    mock_report_service_get_metadata.assert_called_once_with(db=ANY, report_id=report_id)


def test_download_report_file_csv_success(
    authenticated_client: TestClient, mock_report_service_get_metadata: MagicMock,
    temp_reports_dir_module: str, monkeypatch, db: Session
):
    monkeypatch.setattr(settings, "REPORTS_STORAGE_DIR", temp_reports_dir_module)
    report_id = 2; test_user_id = 1
    csv_filename = f"test_report_{report_id}.csv"
    csv_content = "col1,col2\nval1,val2".encode('utf-8') # Store as bytes

    mock_metadata = setup_test_report_file(
        temp_reports_dir_module, report_id, test_user_id, "csv", csv_filename, csv_content
    )
    mock_report_service_get_metadata.return_value = mock_metadata

    response = authenticated_client.get(f"/api/v1/reports/{report_id}/download/csv")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/csv"
    assert response.headers["content-disposition"] == f'attachment; filename="{csv_filename}"'
    assert response.content == csv_content
    mock_report_service_get_metadata.assert_called_once_with(db=ANY, report_id=report_id)


def test_download_report_file_not_completed(
    authenticated_client: TestClient, mock_report_service_get_metadata: MagicMock,
    temp_reports_dir_module: str, monkeypatch, db: Session
):
    monkeypatch.setattr(settings, "REPORTS_STORAGE_DIR", temp_reports_dir_module)
    report_id = 3; test_user_id = 1
    pdf_filename = f"processing_report_{report_id}.pdf"

    # File might exist but report status is not COMPLETED
    # (though typically file_path might not be set until completion)
    file_path = os.path.join(temp_reports_dir_module, pdf_filename)
    with open(file_path, "wb") as f: f.write(b"dummy content")

    mock_metadata = MagicMock(spec=ReportMetadata)
    mock_metadata.id = report_id; mock_metadata.user_id = test_user_id
    mock_metadata.status = "PROCESSING"
    mock_metadata.file_path_pdf = pdf_filename
    mock_report_service_get_metadata.return_value = mock_metadata

    response = authenticated_client.get(f"/api/v1/reports/{report_id}/download/pdf")
    assert response.status_code == 400
    assert "report is not yet completed" in response.json()["detail"].lower()


def test_download_report_file_not_found_on_disk(
    authenticated_client: TestClient, mock_report_service_get_metadata: MagicMock,
    temp_reports_dir_module: str, monkeypatch, db: Session
):
    monkeypatch.setattr(settings, "REPORTS_STORAGE_DIR", temp_reports_dir_module)
    report_id = 4; test_user_id = 1
    mock_metadata = MagicMock(spec=ReportMetadata)
    mock_metadata.id = report_id; mock_metadata.user_id = test_user_id
    mock_metadata.status = "COMPLETED"
    mock_metadata.file_path_pdf = "non_existent_file.pdf" # File doesn't actually exist on disk
    mock_report_service_get_metadata.return_value = mock_metadata

    response = authenticated_client.get(f"/api/v1/reports/{report_id}/download/pdf")
    assert response.status_code == 404
    assert "file was not found on the server" in response.json()["detail"].lower()

def test_download_report_unauthorized(
    client: TestClient, # Unauthenticated client
    mock_report_service_get_metadata: MagicMock,
    temp_reports_dir_module: str, monkeypatch, db: Session
):
    monkeypatch.setattr(settings, "REPORTS_STORAGE_DIR", temp_reports_dir_module)
    report_id = 5; owner_user_id = 99 # Report owned by a different user
    pdf_filename = f"other_user_report_{report_id}.pdf"

    mock_metadata = setup_test_report_file( # File physically exists
        temp_reports_dir_module, report_id, owner_user_id, "pdf", pdf_filename, b"secret content"
    )
    mock_report_service_get_metadata.return_value = mock_metadata

    # This test uses the unauthenticated `client` fixture from conftest.py
    # The download endpoint is protected by `get_current_active_user`
    unauth_response = client.get(f"/api/v1/reports/{report_id}/download/pdf")
    assert unauth_response.status_code == 401 # Expecting 401 as no token is sent
```
