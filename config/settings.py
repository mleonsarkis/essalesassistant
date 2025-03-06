import os

MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "")
BLOB_CONNECTION_STR = os.getenv("BLOB_CONNECTION_STR", "")
CONTAINER_NAME="salesbotdrafts"