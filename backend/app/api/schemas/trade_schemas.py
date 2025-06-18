from pydantic import BaseModel, Field
from typing import Optional, List
import datetime
from .user_schemas import UserResponse # Assuming user_schemas.py exists or will be created
# from ..models.models import Trade # To get enum like values if defined there for status/type
# ForwardRef might be needed if there are circular dependencies with UserResponse, AssetResponse etc.
# from typing import ForwardRef
# UserResponse = ForwardRef('UserResponse') # Example

# Placeholder for Asset schema - ideally this would be more detailed
class AssetTickerSchema(BaseModel):
    ticker: str

    class Config:
        orm_mode = True


class TradeBase(BaseModel):
    asset1_ticker: str = Field(..., description="Ticker of the first asset (e.g., the one bought in a long leg)")
    asset2_ticker: str = Field(..., description="Ticker of the second asset (e.g., the one sold in a short leg)")

    trade_type: str = Field(default="LONG_SHORT_ENTRY", description="Type of trade action, e.g., LONG_SHORT_ENTRY, EXIT_ALL")
    status: str = Field(default="OPEN", description="Status of the trade, e.g., OPEN, CLOSED, PENDING")

    entry_price_asset1: Optional[float] = None
    entry_price_asset2: Optional[float] = None
    entry_spread_or_ratio: Optional[float] = None
    entry_zscore: Optional[float] = None

    quantity_asset1: float = Field(..., description="Quantity of asset1. Positive for long, negative for short (though usually handled by asset1_is_long).")
    quantity_asset2: float = Field(..., description="Quantity of asset2. Positive for long, negative for short.")
    # Or, define legs more explicitly:
    # long_asset_ticker: str
    # short_asset_ticker: str
    # long_quantity: float
    # short_quantity: float

    cointegrated_pair_id: Optional[int] = Field(None, description="ID of the CointegratedPair entry if trade is based on it")
    notes: Optional[str] = None
    stop_loss_level: Optional[float] = Field(None, description="Value of spread/ratio or Z-score for stop loss")
    take_profit_level: Optional[float] = Field(None, description="Value of spread/ratio or Z-score for take profit")

class TradeCreate(TradeBase):
    user_id: Optional[int] = Field(None, description="User ID if initiated by a user. Nullable for system trades.")
    pass # Inherits all from TradeBase, can add specifics for creation if needed

class TradeUpdate(BaseModel):
    status: Optional[str] = None
    exit_datetime: Optional[datetime.datetime] = None
    exit_price_asset1: Optional[float] = None
    exit_price_asset2: Optional[float] = None
    exit_spread_or_ratio: Optional[float] = None
    exit_zscore: Optional[float] = None
    realized_pnl: Optional[float] = None
    notes: Optional[str] = None
    stop_loss_level: Optional[float] = None
    take_profit_level: Optional[float] = None

class TradeResponse(TradeBase):
    id: int
    user_id: Optional[int] = None
    user: Optional[UserResponse] = None # Include user details; requires UserResponse schema

    entry_datetime: datetime.datetime

    exit_datetime: Optional[datetime.datetime] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None # This would typically be calculated on the fly

    asset1: Optional[AssetTickerSchema] = None # Include basic asset info
    asset2: Optional[AssetTickerSchema] = None

    class Config:
        orm_mode = True

# Add UserResponse to TradeResponse if not done via ForwardRef
# TradeResponse.update_forward_refs() # Not strictly needed here as UserResponse is fully defined before use
# However, if UserResponse itself contained TradeResponse, ForwardRef would be essential.

# To make the user field in TradeResponse work correctly with ORM mode and relationships,
# we need to ensure that when a Trade object is loaded, its 'user' relationship attribute
# can be properly serialized into a UserResponse.
# This is generally handled by Pydantic's orm_mode if relationships are correctly set up in SQLAlchemy models
# and the query populates the relationship (e.g. using joinedload).
# For now, the simple definition might work, but complex cases might require `update_forward_refs`
# or specific handling in the service/route layer to populate nested models.

# Let's try explicitly updating forward refs, though it might not be strictly necessary here
# as UserResponse is fully defined. It's good practice if schemas become more intertwined.
TradeResponse.update_forward_refs()
