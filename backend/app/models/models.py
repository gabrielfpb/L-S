from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps
from ..core.database import Base # Assuming Base is defined in core.database
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    trades = relationship("Trade", back_populates="user")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False) # e.g., PETR4.SA
    name = Column(String, nullable=True) # e.g., Petroleo Brasileiro S.A.
    asset_type = Column(String, default="Stock") # e.g., Stock, ETF
    exchange = Column(String, default="B3") # e.g., B3, NYSE
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # If trades are directly linked to assets (e.g. for single asset trades, not pairs)
    # trades_leg1 = relationship("Trade", foreign_keys="[Trade.asset1_id]", back_populates="asset1")
    # trades_leg2 = relationship("Trade", foreign_keys="[Trade.asset2_id]", back_populates="asset2")


class CointegratedPair(Base):
    __tablename__ = "cointegrated_pairs"

    id = Column(Integer, primary_key=True, index=True)
    asset_y_ticker = Column(String, ForeignKey("assets.ticker"), nullable=False) # Ticker for Y
    asset_x_ticker = Column(String, ForeignKey("assets.ticker"), nullable=False) # Ticker for X

    adf_statistic = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    hedge_ratio_beta_x = Column(Float, nullable=True) # Beta of X when Y is dependent
    ols_constant = Column(Float, nullable=True)
    n_observations_in_test = Column(Integer, nullable=True)

    # Store the parameters used for this test run
    test_data_start_date = Column(DateTime(timezone=True), nullable=True)
    test_data_end_date = Column(DateTime(timezone=True), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), server_default=func.now())

    # Store current state (optional, could be calculated on the fly or updated by a job)
    current_spread_value = Column(Float, nullable=True)
    current_zscore = Column(Float, nullable=True)
    zscore_window = Column(Integer, nullable=True) # Window used for current_zscore
    last_zscore_updated_at = Column(DateTime(timezone=True), nullable=True)

    is_active_signal = Column(Boolean, default=False) # If this pair is currently flagged for trading

    # Relationships to Asset table to easily fetch Asset details
    asset_y = relationship("Asset", foreign_keys=[asset_y_ticker])
    asset_x = relationship("Asset", foreign_keys=[asset_x_ticker])

    __table_args__ = (UniqueConstraint('asset_y_ticker', 'asset_x_ticker', name='uq_asset_pair_yx'),)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable if system trades

    # Pair being traded (referencing CointegratedPair or individual assets)
    # Option 1: Link to a CointegratedPair entry
    cointegrated_pair_id = Column(Integer, ForeignKey("cointegrated_pairs.id"), nullable=True)

    # Option 2: Store tickers directly (more flexible if not always from CointegratedPair table)
    asset1_ticker = Column(String, ForeignKey("assets.ticker"), nullable=False) # e.g., Long this one
    asset2_ticker = Column(String, ForeignKey("assets.ticker"), nullable=False) # e.g., Short this one

    trade_type = Column(String, nullable=False) # e.g., "LONG_SHORT_ENTRY", "LONG_SHORT_EXIT"
    status = Column(String, default="OPEN") # e.g., OPEN, CLOSED, CANCELLED

    # Entry details
    entry_datetime = Column(DateTime(timezone=True), server_default=func.now())
    entry_price_asset1 = Column(Float, nullable=True)
    entry_price_asset2 = Column(Float, nullable=True)
    entry_spread_or_ratio = Column(Float, nullable=True) # Value of spread/ratio at entry
    entry_zscore = Column(Float, nullable=True) # Z-score at entry
    quantity_asset1 = Column(Float, nullable=True) # Can be shares or monetary value
    quantity_asset2 = Column(Float, nullable=True)

    # Exit details (if applicable)
    exit_datetime = Column(DateTime(timezone=True), nullable=True)
    exit_price_asset1 = Column(Float, nullable=True)
    exit_price_asset2 = Column(Float, nullable=True)
    exit_spread_or_ratio = Column(Float, nullable=True)
    exit_zscore = Column(Float, nullable=True)

    # P&L
    realized_pnl = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True) # Could be updated by a periodic task

    # Stop Loss / Take Profit levels (values of spread/ratio or Z-score)
    stop_loss_level = Column(Float, nullable=True)
    take_profit_level = Column(Float, nullable=True)

    notes = Column(String, nullable=True) # User or system notes about the trade

    user = relationship("User", back_populates="trades")
    # cointegrated_pair_entry = relationship("CointegratedPair") # If using cointegrated_pair_id

    # Relationships to Asset table for asset1 and asset2
    asset1 = relationship("Asset", foreign_keys=[asset1_ticker])
    asset2 = relationship("Asset", foreign_keys=[asset2_ticker])


from sqlalchemy.dialects.postgresql import JSONB # For parameters

class ReportMetadata(Base):
    __tablename__ = "report_metadata"

    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(String, nullable=True) # e.g., "Daily Summary 2023-10-26"
    report_type = Column(String, nullable=False, index=True) # e.g., "DAILY_SUMMARY", "BACKTEST_ZSCORE_V1"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Link to user if report is user-specific

    generation_requested_at = Column(DateTime(timezone=True), server_default=func.now())
    generation_started_at = Column(DateTime(timezone=True), nullable=True)
    generation_completed_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String, default="PENDING", nullable=False, index=True) # PENDING, PROCESSING, COMPLETED, FAILED

    parameters = Column(JSONB, nullable=True) # Store parameters used for generation (e.g., backtest settings)

    # Store results/summary directly or link to files
    summary_data = Column(JSONB, nullable=True) # For small summary data
    error_message = Column(String, nullable=True) # If generation failed

    # File paths - these would be relative to a configured reports storage directory
    file_path_pdf = Column(String, nullable=True)
    file_path_csv = Column(String, nullable=True)
    # Or store full URLs if files are on S3, etc.
    # download_url_pdf = Column(String, nullable=True)
    # download_url_csv = Column(String, nullable=True)

    celery_task_id = Column(String, nullable=True, index=True) # To track the Celery task

    user = relationship("User") # If user_id is used

    def __repr__(self):
        return f"<ReportMetadata(id={self.id}, type='{self.report_type}', status='{self.status}')>"
