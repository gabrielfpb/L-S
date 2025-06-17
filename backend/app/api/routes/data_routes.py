from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..services import data_collector
from ..schemas.data_schemas import AssetDataResponse, AssetPricePoint, AvailableAssetsResponse, AssetDataParams
import pandas as pd

router = APIRouter()

@router.post("/data/asset_history", response_model=AssetDataResponse)
async def get_asset_historical_data(params: AssetDataParams):
    """
    Endpoint to fetch historical price data for a specific asset.
    Expects a JSON body with "ticker", "start_date", and "end_date".
    """
    try:
        df = data_collector.fetch_asset_data(params.ticker, params.start_date, params.end_date)
        if df.empty:
            return AssetDataResponse(ticker=params.ticker, data=[])

        # Convert DataFrame to list of AssetPricePoint
        price_points = [
            AssetPricePoint(timestamp=index.to_pydatetime(), price=row['price'])
            for index, row in df.iterrows()
        ]
        return AssetDataResponse(ticker=params.ticker, data=price_points)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/data/available_assets", response_model=AvailableAssetsResponse)
async def list_available_assets():
    """
    Endpoint to get a list of all available asset tickers.
    """
    try:
        assets = data_collector.get_available_assets()
        return AvailableAssetsResponse(assets=assets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
