from fastapi import FastAPI
from app.api.routes import data_routes
from app.api.routes import cointegration_routes # New import

app = FastAPI(title="Long & Short Quant API")

@app.get("/")
async def root():
    return {"message": "Welcome to Long & Short Quant API"}

# Include routers
app.include_router(data_routes.router, prefix="/api/v1", tags=["Market Data"])
app.include_router(cointegration_routes.router, prefix="/api/v1", tags=["Cointegration Analysis"]) # New router
# Example for future routers:
# app.include_router(trade_routes.router, prefix="/api/v1", tags=["Trading"])
# app.include_router(auth_routes.router, prefix="/api/v1", tags=["Authentication"])
