# backend/app/core/redis_utils.py
"""
Centralized Redis client initialization and utility functions.

This module provides a shared Redis client instance (`redis_client`) for the application.
It attempts to connect to Redis using the `REDIS_URL` from application settings.
If the connection fails or `REDIS_URL` is not configured, `redis_client` will be `None`,
allowing services that use it to degrade gracefully (e.g., by disabling caching).

The client is configured with `decode_responses=False` by default, meaning it
handles values as bytes. Services using this client for storing complex objects
(like Pandas DataFrames) are responsible for their own serialization/deserialization
to and from bytes (e.g., JSON string to UTF-8 bytes). Example helper functions
for JSON serialization/deserialization (`set_json_data`, `get_json_data`) are commented
out below and can be adapted if needed for general JSON storage with this client.
"""
import redis
from typing import Optional # Added for type hinting redis_client
from .config import settings # To get REDIS_URL

# Shared Redis client instance. It will be None if connection fails or REDIS_URL is not set.
redis_client: Optional[redis.Redis] = None

try:
    if settings.REDIS_URL: # Ensure REDIS_URL is configured
        # decode_responses=False: Store/retrieve bytes. DataFrame caching handles its own encoding/decoding.
        # If this client were for general string/JSON storage, decode_responses=True might be preferred,
        # requiring services to handle encoding if they store bytes, or this util to handle it.
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
        redis_client.ping() # Verify connection
        print("Successfully connected to Redis (via redis_utils module).")
    else:
        print("REDIS_URL not configured. Redis client not initialized (via redis_utils).")
        redis_client = None # Explicitly None if no URL

except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis (via redis_utils): {e}. Redis-dependent features may be disabled or fail.")
    redis_client = None
except Exception as e: # Catch other potential errors during initialization
    print(f"An unexpected error occurred initializing Redis client (via redis_utils): {e}")
    redis_client = None

# Example of generic helpers (optional for now, as DataFrame logic is specific)
# import json
# from typing import Any

# def set_json_data(key: str, value: Any, ttl_seconds: Optional[int] = None):
#     """Serializes a Python object to JSON string and stores it in Redis."""
#     if redis_client:
#         try:
#             # Ensure redis_client uses decode_responses=True for this to work seamlessly with json.loads,
#             # OR handle bytes encoding/decoding here if client is bytes-only.
#             # If redis_client (decode_responses=False) stores bytes:
#             serialized_value = json.dumps(value).encode('utf-8')
#             if ttl_seconds:
#                 redis_client.setex(key, ttl_seconds, serialized_value)
#             else:
#                 redis_client.set(key, serialized_value)
#         except Exception as e:
#             print(f"Error setting JSON in Redis for key {key}: {e}")


# def get_json_data(key: str) -> Optional[Any]:
#     """Retrieves a JSON string from Redis and deserializes it to a Python object."""
#     if redis_client:
#         try:
#             value_bytes = redis_client.get(key) # This will be bytes if decode_responses=False
#             if value_bytes:
#                 return json.loads(value_bytes.decode('utf-8'))
#         except Exception as e:
#             print(f"Error getting/decoding JSON from Redis for key {key}: {e}")
#     return None
```
