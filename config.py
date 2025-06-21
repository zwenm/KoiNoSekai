# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan")

WAIFU_DATA_FILE = "data/waifu_data.json"