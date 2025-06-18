from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..models.models import Trade, Asset, User # Import your SQLAlchemy models
from ..api.schemas.trade_schemas import TradeCreate, TradeUpdate # Import Pydantic schemas
import datetime

def create_trade(db: Session, trade_data: TradeCreate) -> Trade:
    """
    Creates a new trade in the database.
    """
    # Ensure related assets exist, or handle creation/fetching
    asset1 = db.query(Asset).filter(Asset.ticker == trade_data.asset1_ticker).first()
    if not asset1:
        # For now, create asset if not found. In a real app, this might be handled differently
        # or assets would be pre-populated.
        asset1 = Asset(ticker=trade_data.asset1_ticker, name=trade_data.asset1_ticker, asset_type="Stock", exchange="Unknown")
        db.add(asset1)
        # db.commit() # Commit here or let the main commit for trade handle it
        # db.refresh(asset1)

    asset2 = db.query(Asset).filter(Asset.ticker == trade_data.asset2_ticker).first()
    if not asset2:
        asset2 = Asset(ticker=trade_data.asset2_ticker, name=trade_data.asset2_ticker, asset_type="Stock", exchange="Unknown")
        db.add(asset2)
        # db.commit()
        # db.refresh(asset2)

    # If user_id is provided, check if user exists
    if trade_data.user_id:
        user = db.query(User).filter(User.id == trade_data.user_id).first()
        if not user:
            raise ValueError(f"User with ID {trade_data.user_id} not found.")


    db_trade = Trade(
        user_id=trade_data.user_id,
        asset1_ticker=trade_data.asset1_ticker,
        asset2_ticker=trade_data.asset2_ticker,
        trade_type=trade_data.trade_type,
        status=trade_data.status, # Default is OPEN from schema
        entry_datetime=datetime.datetime.now(datetime.timezone.utc), # Ensure timezone aware
        entry_price_asset1=trade_data.entry_price_asset1,
        entry_price_asset2=trade_data.entry_price_asset2,
        entry_spread_or_ratio=trade_data.entry_spread_or_ratio,
        entry_zscore=trade_data.entry_zscore,
        quantity_asset1=trade_data.quantity_asset1,
        quantity_asset2=trade_data.quantity_asset2,
        cointegrated_pair_id=trade_data.cointegrated_pair_id,
        notes=trade_data.notes,
        stop_loss_level=trade_data.stop_loss_level,
        take_profit_level=trade_data.take_profit_level
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def get_trade_by_id(db: Session, trade_id: int) -> Optional[Trade]:
    """
    Retrieves a single trade by its ID, including related user and asset objects.
    """
    return db.query(Trade).options(
        joinedload(Trade.user),
        joinedload(Trade.asset1),
        joinedload(Trade.asset2)
    ).filter(Trade.id == trade_id).first()

def get_trades(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None) -> List[Trade]:
    """
    Retrieves a list of trades, with optional pagination and user filtering.
    Includes related user and asset objects.
    """
    query = db.query(Trade).options(
        joinedload(Trade.user),
        joinedload(Trade.asset1),
        joinedload(Trade.asset2)
    )
    if user_id is not None:
        query = query.filter(Trade.user_id == user_id)
    return query.order_by(Trade.entry_datetime.desc()).offset(skip).limit(limit).all()

def update_trade(db: Session, trade_id: int, trade_update_data: TradeUpdate) -> Optional[Trade]:
    """
    Updates an existing trade.
    """
    db_trade = get_trade_by_id(db, trade_id) # This will fetch with related objects
    if not db_trade:
        return None

    update_data = trade_update_data.dict(exclude_unset=True) # Get only provided fields

    for key, value in update_data.items():
        setattr(db_trade, key, value)

    # Basic P&L calculation if trade is being closed
    if db_trade.status == "CLOSED" and trade_update_data.status == "CLOSED":
        if db_trade.realized_pnl is None : # Calculate only if not already set
            pnl = 0.0
            # Ensure all necessary fields for P&L calculation are present
            if (db_trade.exit_price_asset1 is not None and
                db_trade.entry_price_asset1 is not None and
                db_trade.quantity_asset1 is not None):
                pnl += (db_trade.exit_price_asset1 - db_trade.entry_price_asset1) * db_trade.quantity_asset1

            if (db_trade.exit_price_asset2 is not None and
                db_trade.entry_price_asset2 is not None and
                db_trade.quantity_asset2 is not None):
                # Assuming asset2 is the short leg, so profit if exit price is lower
                pnl += (db_trade.entry_price_asset2 - db_trade.exit_price_asset2) * db_trade.quantity_asset2

            db_trade.realized_pnl = pnl
            if db_trade.exit_datetime is None: # Set exit time if closing now
                db_trade.exit_datetime = datetime.datetime.now(datetime.timezone.utc)


    db.commit()
    db.refresh(db_trade)
    # Re-fetch with relationships to ensure they are current for the response
    db.refresh(db_trade.user) if db_trade.user else None
    db.refresh(db_trade.asset1) if db_trade.asset1 else None
    db.refresh(db_trade.asset2) if db_trade.asset2 else None
    return db_trade

def delete_trade(db: Session, trade_id: int) -> bool:
    """
    Deletes a trade by its ID. Returns True if deleted, False otherwise.
    """
    db_trade = db.query(Trade).filter(Trade.id == trade_id).first() # Simpler fetch for delete
    if db_trade:
        db.delete(db_trade)
        db.commit()
        return True
    return False
