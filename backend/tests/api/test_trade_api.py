from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.api.schemas.trade_schemas import TradeCreate
from app.models import models as db_models

# Fixture for a specific test user (can be defined in conftest.py or here)
# For this example, assuming authenticated_client uses a default test user.

def test_create_trade_authenticated(authenticated_client: TestClient, db: Session):
    # Ensure assets exist for the trade
    # This could also be part of a fixture if multiple tests need these assets
    asset1_ticker_symbol = "TESTPETR4.SA"
    asset2_ticker_symbol = "TESTVALE3.SA"

    asset1 = db.query(db_models.Asset).filter(db_models.Asset.ticker == asset1_ticker_symbol).first()
    if not asset1:
        asset1 = db_models.Asset(ticker=asset1_ticker_symbol, name="Test Petrobras PN")
        db.add(asset1)
    asset2 = db.query(db_models.Asset).filter(db_models.Asset.ticker == asset2_ticker_symbol).first()
    if not asset2:
        asset2 = db_models.Asset(ticker=asset2_ticker_symbol, name="Test Vale ON")
        db.add(asset2)
    db.commit() # Commit assets so trade can reference them

    trade_data_dict = {
        "asset1_ticker": asset1_ticker_symbol,
        "asset2_ticker": asset2_ticker_symbol,
        "trade_type": "LONG_SHORT_ENTRY",
        "quantity_asset1": 100.0,
        "quantity_asset2": 50.0,
        "entry_price_asset1": 30.50,
        "entry_price_asset2": 70.25,
        "entry_zscore": -2.05,
        "notes": "Test trade creation"
        # user_id is not sent, backend will use authenticated user's ID
    }

    response = authenticated_client.post("/api/v1/trades/", json=trade_data_dict)

    assert response.status_code == 201, response.text # Include response text on error
    data = response.json()
    assert data["asset1_ticker"] == asset1_ticker_symbol
    assert data["asset2_ticker"] == asset2_ticker_symbol
    assert data["quantity_asset1"] == 100.0
    assert data["status"] == "OPEN"
    assert data["id"] is not None
    assert data["user_id"] is not None # Should be populated by the backend

    # Check if trade is in DB
    trade_in_db = db.query(db_models.Trade).filter(db_models.Trade.id == data["id"]).first()
    assert trade_in_db is not None
    assert trade_in_db.asset1_ticker == asset1_ticker_symbol
    assert trade_in_db.user_id == data["user_id"]


def test_get_trades_unauthenticated(client: TestClient):
    response = client.get("/api/v1/trades/")
    # ProtectedRoute in frontend, but backend API routes also get protected.
    # The /trades/ GET endpoint is protected by get_current_active_user.
    assert response.status_code == 401 # Expect 401 Unauthorized


def test_get_my_trades_authenticated(authenticated_client: TestClient, db: Session):
    # First, ensure there's at least one trade for the authenticated user
    # The user_id for "authenticated_client" is implicitly set by the fixture
    # We can retrieve it if needed, or just assume trades created by it are linked

    # Create a trade first (similar to test_create_trade_authenticated)
    asset1_ticker_symbol = "MYTRADE_A1.SA"
    asset2_ticker_symbol = "MYTRADE_A2.SA"
    asset1 = db.query(db_models.Asset).filter(db_models.Asset.ticker == asset1_ticker_symbol).first()
    if not asset1: db.add(db_models.Asset(ticker=asset1_ticker_symbol));
    asset2 = db.query(db_models.Asset).filter(db_models.Asset.ticker == asset2_ticker_symbol).first()
    if not asset2: db.add(db_models.Asset(ticker=asset2_ticker_symbol));
    db.commit()

    trade_data_dict = {
        "asset1_ticker": asset1_ticker_symbol, "asset2_ticker": asset2_ticker_symbol,
        "trade_type": "LONG_SHORT_ENTRY", "quantity_asset1": 10, "quantity_asset2": 20,
    }
    create_response = authenticated_client.post("/api/v1/trades/", json=trade_data_dict)
    assert create_response.status_code == 201
    created_trade_id = create_response.json()["id"]

    # Now, try to get trades
    response = authenticated_client.get("/api/v1/trades/")
    assert response.status_code == 200
    trades_list = response.json()
    assert isinstance(trades_list, list)
    # Check if the created trade is in the list
    found = any(trade['id'] == created_trade_id for trade in trades_list)
    assert found, "Newly created trade not found in the list of user's trades."
```
