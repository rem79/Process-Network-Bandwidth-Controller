import sqlite3
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Persistent Directory in AppData
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AntigravityNetworkSentinel')
os.makedirs(APPDATA_DIR, exist_ok=True)
DB_PATH = os.path.join(APPDATA_DIR, "traffic_history.db")

class HistoryDB:
    """
    SQLite-backed traffic metrics persistence and analytics engine.
    Stores high-frequency process traffic samples and aggregates daily/hourly statistics.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        pid INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        exe TEXT,
                        up_bytes REAL NOT NULL,
                        down_bytes REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_samples_time ON traffic_samples(timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_samples_name_time ON traffic_samples(name, timestamp)
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_process_stats (
                        date TEXT NOT NULL,
                        name TEXT NOT NULL,
                        exe TEXT,
                        total_up_bytes REAL DEFAULT 0,
                        total_down_bytes REAL DEFAULT 0,
                        last_updated REAL,
                        PRIMARY KEY (date, name)
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_process_stats(date)
                """)
                conn.commit()
                logging.info(f"Initialized traffic history database schema at {self.db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize database schema: {e}")

    def record_traffic_batch(self, samples: List[Dict[str, Any]]):
        """
        Records a batch of process traffic samples and updates daily aggregates.
        samples: list of dicts with keys: pid, name, exe, up_bytes, down_bytes, timestamp
        """
        if not samples:
            return

        curr_time = time.time()
        today_str = datetime.fromtimestamp(curr_time).strftime('%Y-%m-%d')

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                sample_rows = []
                for s in samples:
                    up_b = float(s.get('up_bytes', 0.0))
                    down_b = float(s.get('down_bytes', 0.0))
                    if up_b <= 0 and down_b <= 0:
                        continue
                    ts = float(s.get('timestamp', curr_time))
                    name = str(s.get('name', 'Unknown'))
                    exe = str(s.get('exe', ''))
                    pid = int(s.get('pid', 0))

                    sample_rows.append((ts, pid, name, exe, up_b, down_b))

                    # Update or insert daily aggregate
                    cursor.execute("""
                        INSERT INTO daily_process_stats (date, name, exe, total_up_bytes, total_down_bytes, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date, name) DO UPDATE SET
                            total_up_bytes = total_up_bytes + excluded.total_up_bytes,
                            total_down_bytes = total_down_bytes + excluded.total_down_bytes,
                            exe = CASE WHEN excluded.exe != '' THEN excluded.exe ELSE daily_process_stats.exe END,
                            last_updated = excluded.last_updated
                    """, (today_str, name, exe, up_b, down_b, ts))

                if sample_rows:
                    cursor.executemany("""
                        INSERT INTO traffic_samples (timestamp, pid, name, exe, up_bytes, down_bytes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, sample_rows)

                conn.commit()
        except Exception as e:
            logging.error(f"Error saving traffic batch: {e}")

    def get_top_consumers(self, period_hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns top network consumers over the specified hourly window.
        """
        since_time = time.time() - (period_hours * 3600)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, exe,
                           SUM(up_bytes) as total_up,
                           SUM(down_bytes) as total_down,
                           SUM(up_bytes + down_bytes) as total_traffic
                    FROM traffic_samples
                    WHERE timestamp >= ?
                    GROUP BY name
                    ORDER BY total_traffic DESC
                    LIMIT ?
                """, (since_time, limit))
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "name": r["name"],
                        "exe": r["exe"],
                        "total_up_bytes": r["total_up"],
                        "total_down_bytes": r["total_down"],
                        "total_traffic_bytes": r["total_traffic"]
                    })
                return results
        except Exception as e:
            logging.error(f"Error fetching top consumers: {e}")
            return []

    def get_timeline_stats(self, minutes: int = 60, bucket_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Returns bucketed time-series traffic stats for plotting timeline graphs.
        """
        since_time = time.time() - (minutes * 60)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Bucket timestamps using integer division
                cursor.execute("""
                    SELECT CAST(timestamp / ? AS INT) * ? as bucket_time,
                           SUM(up_bytes) as total_up,
                           SUM(down_bytes) as total_down
                    FROM traffic_samples
                    WHERE timestamp >= ?
                    GROUP BY bucket_time
                    ORDER BY bucket_time ASC
                """, (bucket_seconds, bucket_seconds, since_time))
                rows = cursor.fetchall()
                timeline = []
                for r in rows:
                    timeline.append({
                        "timestamp": r["bucket_time"],
                        "time_str": datetime.fromtimestamp(r["bucket_time"]).strftime('%H:%M'),
                        "up_bytes": r["total_up"],
                        "down_bytes": r["total_down"],
                        "up_kbps": (r["total_up"] / bucket_seconds) / 1024,
                        "down_kbps": (r["total_down"] / bucket_seconds) / 1024
                    })
                return timeline
        except Exception as e:
            logging.error(f"Error fetching timeline stats: {e}")
            return []

    def get_daily_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Returns daily aggregated traffic history across all applications.
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT date, name, exe, total_up_bytes, total_down_bytes,
                           (total_up_bytes + total_down_bytes) as total_bytes
                    FROM daily_process_stats
                    WHERE date >= ?
                    ORDER BY date DESC, total_bytes DESC
                """, (since_date,))
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "date": r["date"],
                        "name": r["name"],
                        "exe": r["exe"],
                        "total_up_bytes": r["total_up_bytes"],
                        "total_down_bytes": r["total_down_bytes"],
                        "total_bytes": r["total_bytes"]
                    })
                return results
        except Exception as e:
            logging.error(f"Error fetching daily history: {e}")
            return []

    def cleanup_old_samples(self, retention_days: int = 14):
        """
        Cleans up granular high-frequency sample records older than retention_days.
        Daily aggregated statistics are preserved.
        """
        cutoff_time = time.time() - (retention_days * 86400)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM traffic_samples WHERE timestamp < ?", (cutoff_time,))
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    logging.info(f"Cleaned up {deleted} old traffic sample records.")
        except Exception as e:
            logging.error(f"Error cleaning up old samples: {e}")

# Global Singleton Instance
history_db = HistoryDB()
