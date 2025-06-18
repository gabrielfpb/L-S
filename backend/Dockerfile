# backend/Dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies (if any, e.g., for psycopg2 build if not using -binary)
# RUN apt-get update && apt-get install -y ... && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy requirements first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy entrypoint script (for running migrations then app)
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy the rest of the application code
COPY . /app

# The entrypoint will handle running migrations and then starting the app
# Uvicorn will be started by the entrypoint script.
# EXPOSE 8000 # Port exposed by Uvicorn, good for documentation but not strictly needed for Docker Compose linking

ENTRYPOINT ["/app/entrypoint.sh"]
# Default command if entrypoint.sh doesn't specify one for app start
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# This CMD will be overridden for the celery worker service in docker-compose.
