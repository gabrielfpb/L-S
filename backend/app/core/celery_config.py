# backend/app/core/celery_config.py
from ..core.config import settings # Main application settings

# Celery configuration
# Using Redis as the message broker and result backend
CELERY_BROKER_URL = settings.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = settings.CELERY_RESULT_BACKEND

# Example: Task settings (can be expanded)
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC' # Recommended for Celery
CELERY_ENABLE_UTC = True
# CELERY_TASK_TRACK_STARTED = True # If you want to track 'STARTED' state
# CELERY_TASK_SEND_SENT_EVENT = True # If you want to send sent events

# Example: Define a simple queue if needed, or rely on default
# from kombu import Queue
# CELERY_TASK_QUEUES = (
#     Queue('default', routing_key='task.#'),
#     Queue('high_priority', routing_key='high_priority.#'),
# )
# CELERY_TASK_DEFAULT_QUEUE = 'default'
# CELERY_TASK_DEFAULT_EXCHANGE = 'tasks'
# CELERY_TASK_DEFAULT_ROUTING_KEY = 'task.default'
