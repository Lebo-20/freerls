import json
import os
import logging
from config import PROCESSED_FILE

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, file_path=PROCESSED_FILE):
        self.file_path = file_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load database: {e}")
                return {}
        return {}

    def _save(self):
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save database: {e}")

    def is_processed(self, drama_id):
        return str(drama_id) in self.data

    def mark_processed(self, drama_id, metadata=None):
        self.data[str(drama_id)] = metadata or True
        self._save()

    def get_last_episode(self, drama_id):
        entry = self.data.get(str(drama_id))
        if isinstance(entry, dict):
            return entry.get("last_episode", 0)
        return 0

    def update_last_episode(self, drama_id, last_ep):
        if str(drama_id) not in self.data:
            self.data[str(drama_id)] = {}
        if isinstance(self.data[str(drama_id)], dict):
            self.data[str(drama_id)]["last_episode"] = last_ep
            self._save()
