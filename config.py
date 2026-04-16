import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# FreeReels API Configuration
FREEREELS_API_KEY = os.getenv("FREEREELS_API_KEY", "YOUR_TOKEN_HERE")
BASE_URL = "https://captain.sapimu.au/freereels/api/v1"
LANG = "id-ID"

# Telegram Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Google Sheets Configuration
SPREADSHEET_ID = "1lRZrBO9YOnzxdjSfcCmrQzKr-aQKDnMd2vD-x90qRj4"
CREDENTIALS_FILE = "credentials.json"
BOT_NAME = "FreeReels"

# Queue & Worker Settings
MAX_WORKERS = 3
SEMAPHORE_LIMIT = 2
AUTO_SCAN_INTERVAL = 15 * 60  # 15 minutes
MAX_CONCURRENT_DOWNLOADS = 3  # Per worker/global limit
DOWNLOAD_DIR = "downloads"
PROCESSED_FILE = "processed.json"

# Priority Levels
PRIORITY_HIGH = 1
PRIORITY_LOW = 2

# FFmpeg Settings
FFMPEG_CRF = 24
FFMPEG_PRESET = "fast"

# Upload Settings
MAX_UPLOAD_SIZE = 1900 * 1024 * 1024 # 1900 MB to be safe
