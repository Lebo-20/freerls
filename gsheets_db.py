import gspread
from google.oauth2.service_account import Credentials
import logging
from config import SPREADSHEET_ID, CREDENTIALS_FILE, BOT_NAME, PROCESSED_FILE
import os
import json

logger = logging.getLogger(__name__)

class GoogleSheetsDB:
    def __init__(self):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.credentials_file = CREDENTIALS_FILE
        self.spreadsheet_id = SPREADSHEET_ID
        self.local_file = PROCESSED_FILE
        self.mode = "local"
        self.client = self._authenticate()
        self.sheet = self._get_sheet()

    def _authenticate(self):
        if not os.path.exists(self.credentials_file):
            logger.warning(f"⚠️ {self.credentials_file} TIDAK DITEMUKAN. Menggunakan Local Database (processed.json).")
            self.mode = "local"
            return None
        try:
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=self.scope)
            self.mode = "gsheets"
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Gagal auth Google Sheets: {e}. Fallback ke local.")
            self.mode = "local"
            return None

    def _get_sheet(self):
        if self.mode == "local" or not self.client: return None
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            sheet = spreadsheet.get_worksheet(0)
            headers = sheet.row_values(1)
            if not headers:
                sheet.insert_row(["Judul Drama", "Status", "Catatan", "Bot"], 1)
            return sheet
        except Exception as e:
            logger.error(f"Failed to access sheet: {e}. Switching to local.")
            self.mode = "local"
            return None

    def _load_local(self):
        if os.path.exists(self.local_file):
            with open(self.local_file, 'r') as f:
                return json.load(f)
        return []

    def _save_local(self, data):
        with open(self.local_file, 'w') as f:
            json.dump(data, f, indent=4)

    def is_processed(self, title):
        title_clean = str(title).strip().lower()
        if self.mode == "gsheets" and self.sheet:
            try:
                all_titles = self.sheet.col_values(1)
                for t in all_titles[1:]:
                    if t.strip().lower() == title_clean:
                        return True
            except Exception as e:
                logger.error(f"Error checking sheet: {e}")
        
        # Always check local as second source or fallback
        local_data = self._load_local()
        for record in local_data:
            if record.get("title", "").strip().lower() == title_clean:
                return True
        return False

    def add_record(self, title, status, note):
        # Add to local
        local_data = self._load_local()
        local_data.append({"title": title, "status": status, "note": note, "bot": BOT_NAME})
        self._save_local(local_data)

        # Add to Sheet if available
        if self.mode == "gsheets" and self.sheet:
            try:
                self.sheet.append_row([title, status, note, BOT_NAME])
            except Exception as e:
                logger.error(f"Failed to add to sheet: {e}")

    def mark_success(self, title):
        self.add_record(title, "BERHASIL", "Upload sukses")

    def mark_fail(self, title, reason="Gagal 2x, skip permanen"):
        self.add_record(title, "GAGAL", reason)

    def mark_skip(self, title):
        self.add_record(title, "SKIP", "Sudah pernah diproses")
