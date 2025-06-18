# backend/app/tasks/example_tasks.py
from celery import shared_task # Use shared_task for better decoupling
import time
from typing import List, Optional, Any, Dict # For type hints
from ..services import data_collector
from ..services import cointegration_analyzer
# from app.core.database import SessionLocal # For direct DB access

@shared_task(name="tasks.add_numbers")
def add_numbers(x: int, y: int) -> int:
    time.sleep(5)
    result = x + y
    print(f"Task add_numbers: {x} + {y} = {result}")
    return result

@shared_task(name="tasks.fetch_all_available_assets_task")
def fetch_all_available_assets_task() -> List[str]:
    print("Task: Fetching all available assets...")
    try:
        assets = data_collector.get_available_assets()
        print(f"Task: Found {len(assets)} assets.")
        return assets
    except Exception as e:
        print(f"Error in fetch_all_available_assets_task: {e}")
        # self.retry(exc=e, countdown=60) # For retries, task needs to be bound: @shared_task(bind=True)
        raise # Re-raise to mark task as failed

@shared_task(name="tasks.run_cointegration_for_pair_task")
def run_cointegration_for_pair_task(ticker_y: str, ticker_x: str) -> Optional[Dict[str, Any]]:
    print(f"Task: Running cointegration for {ticker_y} and {ticker_x}")
    try:
        series_y_data = data_collector.get_asset_data_sample(ticker_y, n_points=300)
        series_x_data = data_collector.get_asset_data_sample(ticker_x, n_points=300)

        if series_y_data.empty or series_x_data.empty:
            print(f"Task: Not enough data for {ticker_y} or {ticker_x}")
            raise ValueError(f"Not enough data for {ticker_y} or {ticker_x}")

        series_y = series_y_data['price']
        series_x = series_x_data['price']

        import pandas as pd
        aligned_data = pd.concat([series_y, series_x], axis=1, join='inner').dropna()
        if len(aligned_data) < 20:
            print(f"Task: Not enough overlapping data for {ticker_y}, {ticker_x} after alignment.")
            raise ValueError(f"Not enough overlapping data for {ticker_y}, {ticker_x}")

        result = cointegration_analyzer.run_engle_granger_test(
            aligned_data.iloc[:,0],
            aligned_data.iloc[:,1]
        )
        print(f"Task: Cointegration result for {ticker_y}, {ticker_x}: p-value {result.get('p_value')}")
        if result.get("error"): # If the test itself returned an error structure
            raise Exception(f"Cointegration test error: {result.get('error')}")
        return result
    except Exception as e:
        print(f"Error in run_cointegration_for_pair_task for {ticker_y}, {ticker_x}: {e}")
        raise # Re-raise to mark task as failed

# Example of a task that might use DB session (careful with session management in tasks)
# @shared_task(name="tasks.record_analysis_result", bind=True) # bind=True to access self
# def record_analysis_result(self, pair_data: dict):
#     db = None
#     try:
#         db = SessionLocal()
#         # ... logic to save pair_data to CointegratedPair model ...
#         # Example: CointegratedPair.create_or_update(db, **pair_data)
#         db.commit()
#         print(f"Result for {pair_data.get('pair')} recorded.")
#     except Exception as e:
#         if db: db.rollback()
#         print(f"Error recording analysis result: {e}")
#         raise self.retry(exc=e, countdown=60, max_retries=3) # Example retry
#     finally:
#         if db: db.close()
