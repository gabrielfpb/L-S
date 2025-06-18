# backend/celery_worker.py
import os
from celery import Celery
# from app.core.config import settings # To access broker/backend URLs directly if not using celery_config.py for everything

# It's common to set the default Django settings module for 'celery' program.
# This is not Django, but we need to ensure our app modules can be imported.
# One way is to ensure the PYTHONPATH includes the app directory.
# If running celery worker from `backend/` directory: `celery -A celery_worker.celery_app worker -l info`
# then imports like `app.tasks` should work if `app` is a package.

# Use environment variable for broker/backend or import from config
# For simplicity here, directly using from settings.py via celery_config.py
# In a real app, you might pass config path or use env vars for broker.
# CELERY_BROKER_URL = settings.CELERY_BROKER_URL
# CELERY_RESULT_BACKEND = settings.CELERY_RESULT_BACKEND

# It's crucial that the Celery app can import the task modules.
# Ensure your PYTHONPATH is set up correctly when running the Celery worker.
# If 'app' is in the same directory or on PYTHONPATH, this should work.

# Option 1: Configure directly (if celery_config.py is not used for URLs)
# celery_app = Celery(
#     "longshortquant_worker",
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND,
#     include=["app.tasks.example_tasks"]  # List of modules to import tasks from
# )

# Option 2: Load config from a separate config object/file (preferred)
# Create the celery application instance
celery_app = Celery("longshortquant_worker")

# Load Celery configuration from celery_config.py
# This requires that 'app.core.celery_config' is importable from where the worker is run.
# If worker is run from `backend/` directory, then `app` package must be in `backend/`.
celery_app.config_from_object("app.core.celery_config") # Path to your celery_config module

# List of modules to search for tasks. Celery will auto-discover @task or @shared_task decorators.
# Adjust these paths based on where your task files will be.
celery_app.autodiscover_tasks(
    packages=[
        "app.tasks" # Assuming tasks will be in app/tasks/__init__.py or app/tasks/some_module.py
    ],
    # Or specify modules directly if preferred:
    # related_name="example_tasks", # Example: app.tasks.example_tasks
)


# Optional: Update Celery configuration with app-specific settings not in celery_config
# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
# )

if __name__ == "__main__":
    # This is for running the worker directly using `python celery_worker.py worker ...`
    # Though typically you run `celery -A celery_worker.celery_app worker ...`
    # For this to work, the current directory needs to be on PYTHONPATH or have app package.
    celery_app.start()
