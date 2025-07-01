# Long & Short Quant

A modern and responsive application for financial consultants to perform cointegration analysis and Long & Short operations on the Brazilian Stock Exchange (B3).

## 🚀 Overview

This application is designed as a robust, intuitive, and highly customizable tool, combining real-time data analysis power with clear visualizations and interactive functionalities. The goal is to transform complex data into actionable insights, enabling consultants to optimize strategies and manage risks effectively.

## 📋 Key Features

### 🔍 Cointegration Analysis
*   **Pair Identification**: Automated algorithm to identify cointegrated asset pairs.
*   **Engle-Granger Test**: Statistical verification of cointegration.
*   **Z-Score Calculation**: Analysis of historical ratio deviations.
*   **Trading Signals**: Automatic generation of recommendations based on statistical thresholds.

### 📊 Interactive Dashboard
*   **Real-Time Metrics**: Visualization of performance, P&L, and trading statistics. (Future)
    *   **Dynamic Charts**: Historical spread and Z-Score charts for selected pairs with interactive controls (date range, Z-score window).
    *   **Current Opportunities**: List of pairs with active trading signals (based on Z-Score).
*   **Performance Tracking**: Historical results tracking. (Future)

### 💼 Trade Management
*   **Trade Creation**: Interface for configuring Long & Short operations.
*   **Ratio Adjustment**: Flexibility to execute orders +/- 0.5% from the suggested ratio. (Conceptual, backend supports price input)
*   **Stop Loss/Take Profit**: Automatic limit configuration. (Conceptual, backend model has fields)
*   **Complete History**: Tracking of all operations.

### 📈 Automated Reports
*   **Daily/Weekly Reports**: Automatic performance summaries. (Backend logic placeholder, UI exists)
    *   **Backtesting Reports**: Analysis of Z-score based strategies using historical market data, with key performance metrics and equity curve visualization.
*   **Email Distribution**: Automatic report distribution. (Future)
    *   **Export**: Multiple formats (PDF, CSV). (Placeholder file generation for report data)

## 🛠️ Technologies Utilized

### Backend
*   **FastAPI**: Modern, fast web framework for building APIs.
    *   **Alpha Vantage API, yfinance library**: For real market data integration.
*   **SQLAlchemy**: ORM for Python.
*   **PostgreSQL**: Main relational database.
*   **Redis**: Cache, message broker for Celery.
*   **Pandas/NumPy**: Data analysis and manipulation.
*   **SciPy/Statsmodels**: Statistical analysis.
*   **Celery**: Asynchronous task processing.
*   **Alembic**: Database migrations.
*   **Passlib & python-jose**: Authentication (password hashing, JWT).

### Frontend
*   **React 18**: Library for building user interfaces.
*   **TypeScript**: Static typing for JavaScript.
*   **Material-UI (MUI)**: UI component library.
*   **React Router**: Client-side routing.
*   **Plotly.js & react-plotly.js**: Interactive charting.
*   **Axios**: HTTP client for API communication.
*   **React Context API**: State management (for authentication).

### Infrastructure
*   **Docker & Docker Compose**: Containerization and local orchestration.
*   **Nginx**: Web server and reverse proxy for the frontend.

## 🏗️ Project Structure

```
.
├── backend/            # FastAPI application (Python)
│   ├── alembic/        # Alembic migration scripts
│   ├── app/            # Main application code
│   │   ├── api/        # API routes and schemas
│   │   ├── core/       # Core logic (config, db, security, celery)
│   │   ├── models/     # SQLAlchemy ORM models
│   │   ├── services/   # Business logic services
│   │   └── tasks/      # Celery tasks
│   ├── tests/          # (Placeholder for tests)
│   ├── .env.example    # Example environment variables (if provided for local dev)
│   ├── Dockerfile
│   ├── entrypoint.sh   # Docker entrypoint for migrations
│   ├── main.py         # FastAPI app entry point
│   └── requirements.txt
├── frontend/           # React application (TypeScript)
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/ # Reusable UI components
│   │   ├── contexts/   # React Context API providers
│   │   ├── pages/      # Page-level components
│   │   ├── services/   # API communication services
│   │   └── store/      # (Placeholder for Redux if used later)
│   ├── .env.example    # Example environment variables (if provided for local dev)
│   ├── Dockerfile
│   ├── nginx.conf      # Nginx configuration
│   └── package.json
├── .dockerignore       # Global .dockerignore (though specific ones are in backend/frontend)
├── .env                # Optional root .env for docker-compose variable substitution
├── docker-compose.yml  # Docker Compose configuration
└── README.md           # This file
```

## ⚙️ Setup and Running the Application (Docker)

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Configure Environment Variables:**
    *   Create a `.env` file in the project root (same directory as `docker-compose.yml`). This file is used by Docker Compose for variable substitution. You can copy `env.example` if provided, or create it based on the defaults in `docker-compose.yml`.
        ```bash
        # Example content for root .env (for docker-compose variable substitution)
        DB_USER=myadmin
        DB_PASSWORD=mysecretpassword
        DB_NAME=lsq_db
        DB_PORT_HOST=5432       # Host port for DB, ensure it's free
        DB_PORT_CONTAINER=5432  # Port inside DB container (usually fixed)

        REDIS_PORT_HOST=6379    # Host port for Redis

        BACKEND_PORT_HOST=8000  # Host port for Backend API

        FRONTEND_PORT_HOST=3000 # Host port for Frontend UI

        SECRET_KEY=a_very_strong_and_random_secret_key_for_jwt_ควรเปลี่ยนค่านี้
        ```
    *   The `backend` and `worker` services in `docker-compose.yml` use environment variables like `DATABASE_URL` and `REDIS_URL` that are constructed using these root `.env` variables and service names (e.g., `db`, `redis`) for inter-container communication.
    *   The `frontend` calls the backend via Nginx proxy. The `frontend/src/services/api.ts` is configured to use `/api/v1` as its base URL, which Nginx proxies.

3.  **Build and Run with Docker Compose:**
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces a rebuild of images if Dockerfiles or their contexts have changed.
    *   `-d`: Runs containers in detached mode.

4.  **Accessing the Application:**
    *   **Frontend UI**: `http://localhost:3000` (or the `FRONTEND_PORT_HOST` you set in your root `.env`).
    *   **Backend API Docs (Swagger UI)**: `http://localhost:8000/docs` (or the `BACKEND_PORT_HOST` you set, then `/docs`).
    *   **Backend API Docs (ReDoc)**: `http://localhost:8000/redoc`.

5.  **Database Migrations:**
    *   Migrations are run automatically by the `entrypoint.sh` script in the `backend` container when it starts.
    *   To run migrations manually (e.g., after creating a new one):
        ```bash
        docker-compose exec backend python -m alembic upgrade head
        ```
    *   To create a new migration (after making changes to `backend/app/models/models.py`):
        ```bash
        docker-compose exec backend python -m alembic revision -m "your_migration_message"
        ```
        Then, inspect the generated script in `backend/alembic/versions/` and apply it using the `upgrade head` command above (or let it run on next container start).

6.  **Stopping the Application:**
    ```bash
    docker-compose down
    ```
    To remove volumes (database data, redis data):
    ```bash
    docker-compose down -v
    ```

## 📄 API Documentation
The backend API documentation is automatically generated by FastAPI and is available when the backend service is running:
*   Swagger UI: `/docs` (e.g., `http://localhost:8000/docs`)
*   ReDoc: `/redoc` (e.g., `http://localhost:8000/redoc`)

## 🧪 Running Tests (Placeholder)
*   **Backend**: (Instructions for pytest if set up, e.g., `docker-compose exec backend pytest`)
*   **Frontend**: (Instructions for Jest/React Testing Library if set up, e.g., `cd frontend && npm test`)

## 🤝 Contributing
(Details on contributing guidelines if this were an open project. E.g., fork, branch, PR.)

## 📜 License
(Specify license, e.g., MIT License. For this project, assume MIT unless specified otherwise.)
This project is licensed under the MIT License - see the LICENSE.md file for details (if one exists).
```
