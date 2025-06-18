from fastapi import FastAPI
# ... other router imports
from app.api.routes import data_routes, cointegration_routes, trade_routes, auth_routes, task_routes, report_routes # Added report_routes

app = FastAPI(title="Long & Short Quant API")

@app.get("/")
async def root():
    return {"message": "Welcome to Long & Short Quant API"}

# Include routers
app.include_router(data_routes.router, prefix="/api/v1", tags=["Market Data"])
app.include_router(cointegration_routes.router, prefix="/api/v1", tags=["Cointegration Analysis"])
app.include_router(trade_routes.router, prefix="/api/v1/trades", tags=["Trade Management"])
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(task_routes.router, prefix="/api/v1/tasks", tags=["Async Tasks"])
app.include_router(report_routes.router, prefix="/api/v1/reports", tags=["Reporting"]) # New Report router
