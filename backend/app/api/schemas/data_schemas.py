from pydantic import BaseModel
from typing import List, Dict
import datetime

class AssetDataParams(BaseModel):
    ticker: str
    start_date: str # Expects "YYYY-MM-DD"
    end_date: str   # Expects "YYYY-MM-DD"

class AssetPricePoint(BaseModel):
    timestamp: datetime.datetime
    price: float

class AssetDataResponse(BaseModel):
    ticker: str
    data: List[AssetPricePoint]

class AvailableAssetsResponse(BaseModel):
    assets: List[str]
