# Backend - Long & Short Quant

This directory contains the FastAPI backend application.

## Overview
The backend provides APIs for:
*   **Market Data**: Fetching historical stock data using Alpha Vantage (primary, requires API key) and yfinance (fallback). Accessed via `/api/v1/data/`.
*   **Cointegration Analysis**: Includes Engle-Granger tests, Z-Score calculation, identification of cointegrated pairs, and an endpoint (`/api/v1/cointegration/pair_historical_data`) for fetching detailed data for charting pair dynamics (spread, rolling stats, Z-score). Accessed via `/api/v1/cointegration/`.
*   **User Authentication & Management**: JWT-based authentication, user registration. Accessed via `/api/v1/auth/`.
*   **Trade Management**: CRUD operations for trades. Accessed via `/api/v1/trades/`.
*   **Asynchronous Task Processing (Celery)**: Used for report generation and other potentially long-running operations. Task status can be checked via `/api/v1/tasks/`.
*   **Reporting**:
    *   Triggering generation of performance summary reports and backtesting reports.
    *   Listing report metadata and allowing download of generated files (placeholder PDF/CSV).
    *   Backtesting uses real market data and a Z-score based strategy, providing key metrics and equity curve data.
    *   Accessed via `/api/v1/reports/`.

## API Documentation
FastAPI automatically generates interactive API documentation when the backend service is running:
*   **Swagger UI**: Accessible at `/docs` (e.g., `http://localhost:8000/docs` when running locally or via Docker).
*   **ReDoc**: Accessible at `/redoc` (e.g., `http://localhost:8000/redoc`).

## Local Development (Without Docker)

1.  **Prerequisites**:
    *   Python 3.9+
    *   PostgreSQL server running
    *   Redis server running

2.  **Setup Virtual Environment**:
    From the `backend/` directory:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    *   Create a `.env` file in this `backend/` directory.
    *   Set the following variables (adjust values as per your local setup):
        ```env
        DATABASE_URL="postgresql://youruser:yourpassword@localhost:5432/yourdbname"
        REDIS_URL="redis://localhost:6379/0"
        CELERY_BROKER_URL="redis://localhost:6379/1"
        CELERY_RESULT_BACKEND="redis://localhost:6379/2"
        SECRET_KEY="your_very_secret_key_for_jwt_local_dev"
            REPORTS_STORAGE_DIR="generated_reports" # Ensure this directory exists
            ALPHA_VANTAGE_API_KEY="YOUR_ALPHA_VANTAGE_KEY" # Optional: for Alpha Vantage data
        ```

5.  **Run Database Migrations**:
    *   Ensure `alembic.ini`'s `sqlalchemy.url` is commented out or points to a dummy URL, as `backend/alembic/env.py` is configured to use `DATABASE_URL` from your `.env` file via `app.core.config.settings`.
    *   If `alembic/` directory doesn't exist (first time setup): `python -m alembic init alembic` (then configure `env.py` and `script.py.mako` as per project setup).
    *   To create an initial migration if models exist but no migration yet: `python -m alembic revision -m "initial schema from models"`
    *   Apply migrations: `python -m alembic upgrade head`

6.  **Run FastAPI Application**:
    From the `backend/` directory (with virtual environment activated):
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

7.  **Run Celery Worker**:
    *   Open a new terminal, navigate to `backend/`, and activate the virtual environment.
    *   From the `backend/` directory:
        ```bash
        celery -A celery_worker.celery_app worker -l info
        # On Windows, you might need -P eventlet:
        # celery -A celery_worker.celery_app worker -l info -P eventlet
        ```

## Database Migrations (Alembic)
From the `backend/` directory with virtual environment activated:
*   **Create a new migration** (after changing SQLAlchemy models in `app/models/models.py`):
    ```bash
    python -m alembic revision -m "description_of_your_change"
    ```
    Inspect the generated script in `alembic/versions/`.
*   **Apply migrations**: `python -m alembic upgrade head`
*   **Downgrade to previous migration**: `python -m alembic downgrade -1`
*   **View current revision**: `python -m alembic current`
*   **View migration history**: `python -m alembic history`

## Environment Variables
Key environment variables used by the application (typically set in `.env` for local dev or via Docker environment settings):
*   `DATABASE_URL`: Full connection string for PostgreSQL.
*   `REDIS_URL`: Connection string for Redis (used by Celery broker/backend).
*   `CELERY_BROKER_URL`: Specific URL for Celery message broker (e.g., `redis://localhost:6379/1`).
*   `CELERY_RESULT_BACKEND`: Specific URL for Celery result backend (e.g., `redis://localhost:6379/2`).
*   `SECRET_KEY`: A strong, random string used for signing JWTs and other security purposes.
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: (Optional) Lifetime of access tokens, defaults to 30 minutes.
*   `REPORTS_STORAGE_DIR`: Directory where generated report files (PDFs, CSVs) are stored. Defaults to `generated_reports` relative to where the app runs.

## Testing
(Placeholder - Add instructions for running backend tests, e.g., with Pytest)
Example:
```bash
# pytest # (If pytest is configured)
```
```
