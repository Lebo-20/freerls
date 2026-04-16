import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import time
from config import DATABASE_URL, BOT_NAME

logger = logging.getLogger(__name__)

class PostgresDB:
    def __init__(self):
        self.url = DATABASE_URL
        self.conn = None
        self._init_db()

    def _connect(self):
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(self.url)
            return self.conn
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            return None

    def _init_db(self):
        conn = self._connect()
        if not conn: return
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS processed_dramas (
                        id SERIAL PRIMARY KEY,
                        title TEXT UNIQUE NOT NULL,
                        status TEXT,
                        note TEXT,
                        bot TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                logger.info("PostgreSQL Database initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")

    def is_processed(self, title):
        title_clean = str(title).strip().lower()
        conn = self._connect()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM processed_dramas WHERE LOWER(title) = %s", (title_clean,))
                return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking PostgreSQL: {e}")
            self.conn = None # Reset connection on error
            return False

    def add_record(self, title, status, note):
        conn = self._connect()
        if not conn: return
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO processed_dramas (title, status, note, bot)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (title) DO UPDATE SET
                    status = EXCLUDED.status,
                    note = EXCLUDED.note,
                    bot = EXCLUDED.bot
                """, (title, status, note, BOT_NAME))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to add record to PostgreSQL: {e}")
            self.conn = None

    def mark_success(self, title):
        self.add_record(title, "BERHASIL", "Upload sukses")

    def mark_fail(self, title, reason="Gagal 2x, skip permanen"):
        self.add_record(title, "GAGAL", reason)

    def mark_skip(self, title):
        self.add_record(title, "SKIP", "Sudah pernah diproses")

    def close(self):
        if self.conn:
            self.conn.close()
