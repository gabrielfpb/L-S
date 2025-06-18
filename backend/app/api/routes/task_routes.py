from fastapi import APIRouter, HTTPException, status
from celery.result import AsyncResult
# Import task functions directly
from ...tasks.example_tasks import add_numbers, fetch_all_available_assets_task, run_cointegration_for_pair_task
from pydantic import BaseModel
from typing import Optional, Any, List # Added List for type hint consistency

router = APIRouter()

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None # Using Any for result type

class AddTaskRequest(BaseModel):
    x: int
    y: int

class CointegrationTaskRequest(BaseModel):
    ticker_y: str
    ticker_x: str

@router.post("/add", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_add_task(request: AddTaskRequest):
    """Enqueues a task to add two numbers."""
    try:
        # .delay() is a shortcut for .apply_async()
        task = add_numbers.delay(request.x, request.y)
        return TaskStatusResponse(task_id=task.id, status=task.status, result=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {e}")


@router.post("/fetch_assets", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_fetch_assets_task():
    """Enqueues a task to fetch all available assets."""
    try:
        task = fetch_all_available_assets_task.delay()
        return TaskStatusResponse(task_id=task.id, status=task.status, result=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {e}")

@router.post("/run_cointegration", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run_cointegration_task(request: CointegrationTaskRequest):
    """Enqueues a task to run cointegration test for a pair."""
    try:
        task = run_cointegration_for_pair_task.delay(request.ticker_y, request.ticker_x)
        return TaskStatusResponse(task_id=task.id, status=task.status, result=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {e}")


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Retrieves the status and result of a Celery task."""
    task_result = AsyncResult(task_id) # Use the task_id to get the AsyncResult object

    result_value: Any = None # Initialize result_value
    current_status = task_result.status

    if task_result.ready():
        if task_result.successful():
            result_value = task_result.get()
        else: # Task failed or was revoked
            try:
                # This will re-raise the exception from the task if propagate=True (default)
                # If propagate=False, it returns the exception instance or error string.
                result_value = task_result.get(propagate=False)
            except Exception as e:
                # This path might not be hit if propagate=False truly returns the exception instance
                result_value = f"Task encountered an error during execution: {str(e)}"

            # If result_value is an Exception instance, convert to string for JSON response
            if isinstance(result_value, Exception):
                result_value = f"Task failed with error: {str(result_value)}"
            elif current_status == 'REVOKED':
                 result_value = "Task was revoked."


    return TaskStatusResponse(
        task_id=task_id,
        status=current_status,
        result=result_value
    )
