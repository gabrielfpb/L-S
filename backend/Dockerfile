FROM python:3.9-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

# Command to run the Uvicorn server
# Make sure main:app is correct and accessible
# The app needs to be in the PYTHONPATH, which WORKDIR and COPY . should handle for main.py
# For app folder, we might need to adjust PYTHONPATH or how uvicorn is called if main.py is outside app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
