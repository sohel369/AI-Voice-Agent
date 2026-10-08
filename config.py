import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BITRIX24_WEBHOOK_URL = os.getenv("BITRIX24_WEBHOOK_URL", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
