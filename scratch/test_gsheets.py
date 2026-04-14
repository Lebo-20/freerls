from gsheets_db import GoogleSheetsDB
import logging

logging.basicConfig(level=logging.INFO)

try:
    db = GoogleSheetsDB()
    # No emojis for windows console safety
    print("SUCCESS: Connected to Google Sheets!")
    print(f"Sheet Name: {db.sheet.title}")
    
except Exception as e:
    print(f"FAILED: {e}")
