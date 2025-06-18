from fastapi import APIRouter, Depends, HTTPException, Query, status # Added status for HTTP codes
from sqlalchemy.orm import Session
from typing import List, Optional
from ..services import trade_service
from ..api.schemas.trade_schemas import TradeCreate, TradeUpdate, TradeResponse
# Import the dependency and UserResponse schema for type hinting
from ..api.dependencies import get_current_active_user
from ..api.schemas.user_schemas import UserResponse
from ..models.models import User as UserModel # Import the SQLAlchemy model User for type hinting current_user

from ..core.database import get_db

router = APIRouter()

@router.post("/", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
def create_new_trade(
    trade: TradeCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Protect this route, current_user is SQLAlchemy model
):
    """
    Create a new trade. Authenticated users only.
    The trade will be associated with the authenticated user.
    """
    # Prevent creating trade for another user unless admin (admin check not implemented here)
    if trade.user_id is not None and trade.user_id != current_user.id:
         # This part of the check might be simplified: just always use current_user.id
         # Or, if superuser functionality is added, they could specify user_id.
         if not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create trade for another user.")

    # Ensure trade is created for the authenticated user if not superuser, or for specified user if superuser
    trade_data_for_service = trade.copy(deep=True) # Use a copy to modify
    if current_user.is_superuser and trade.user_id is not None:
        # Superuser can specify user_id, check if that user exists
        target_user = db.query(UserModel).filter(UserModel.id == trade.user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target user with ID {trade.user_id} not found.")
        trade_data_for_service.user_id = trade.user_id
    else: # Non-superuser or superuser not specifying a user_id
        trade_data_for_service.user_id = current_user.id


    try:
        created_trade = trade_service.create_trade(db=db, trade_data=trade_data_for_service)
        return created_trade
    except ValueError as e: # Catch specific errors from service like "User not found"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log the exception e in a real application
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred.")


@router.get("/{trade_id}", response_model=TradeResponse)
def get_trade_details(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    db_trade = trade_service.get_trade_by_id(db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    if not current_user.is_superuser and db_trade.user_id != current_user.id: # Basic ownership check
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this trade")
    return db_trade

# Other routes (get_all_trades, update_existing_trade, delete_existing_trade)
# would similarly be protected and potentially modified for user ownership checks.

@router.get("/", response_model=List[TradeResponse])
def get_all_trades(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id_filter: Optional[int] = Query(None, description="Filter trades by user ID (admin/superuser use only)", alias="userId"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    user_to_query = current_user.id
    if current_user.is_superuser and user_id_filter is not None:
        # Superuser can filter by any user_id
        user_to_query = user_id_filter
    elif not current_user.is_superuser and user_id_filter is not None and user_id_filter != current_user.id:
        # Non-superuser trying to query another user's trades
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view other users' trades.")

    # If superuser and no filter, they get all trades (user_id=None in service)
    # If non-superuser, they get their own trades (user_id=current_user.id in service)
    effective_user_id_filter = user_to_query if not (current_user.is_superuser and user_id_filter is None) else None

    trades = trade_service.get_trades(db, skip=skip, limit=limit, user_id=effective_user_id_filter)
    return trades

@router.patch("/{trade_id}", response_model=TradeResponse)
def update_existing_trade(
    trade_id: int,
    trade_update: TradeUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    check_trade = trade_service.get_trade_by_id(db, trade_id=trade_id)
    if not check_trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    if not current_user.is_superuser and check_trade.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this trade")

    updated_trade = trade_service.update_trade(db=db, trade_id=trade_id, trade_update_data=trade_update)
    if updated_trade is None: # Should be caught by check_trade already, but good practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found or update failed")
    return updated_trade

@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    check_trade = trade_service.get_trade_by_id(db, trade_id=trade_id)
    if not check_trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    if not current_user.is_superuser and check_trade.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this trade")

    if not trade_service.delete_trade(db=db, trade_id=trade_id):
        # This case should ideally be covered by the check_trade above.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found or could not be deleted")
    return # Return None for 204 response (FastAPI handles this)
