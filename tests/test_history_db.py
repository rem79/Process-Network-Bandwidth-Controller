import os
import tempfile
import time
import unittest
from history_db import HistoryDB

class TestHistoryDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_traffic.db")
        self.db = HistoryDB(db_path=self.db_file)

    def tearDown(self):
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except Exception:
                pass

    def test_init_schema(self):
        self.assertTrue(os.path.exists(self.db.db_path))

    def test_record_and_get_top_consumers(self):
        curr_time = time.time()
        samples = [
            {"pid": 100, "name": "chrome.exe", "exe": "C:\\chrome.exe", "up_bytes": 1024 * 100, "down_bytes": 1024 * 500, "timestamp": curr_time},
            {"pid": 200, "name": "discord.exe", "exe": "C:\\discord.exe", "up_bytes": 1024 * 10, "down_bytes": 1024 * 20, "timestamp": curr_time},
            {"pid": 300, "name": "idle_app.exe", "exe": "", "up_bytes": 0, "down_bytes": 0, "timestamp": curr_time}
        ]

        self.db.record_traffic_batch(samples)
        top = self.db.get_top_consumers(period_hours=1, limit=5)

        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["name"], "chrome.exe")
        self.assertEqual(top[0]["total_down_bytes"], 1024 * 500)
        self.assertEqual(top[0]["total_up_bytes"], 1024 * 100)
        self.assertEqual(top[1]["name"], "discord.exe")

    def test_daily_history(self):
        curr_time = time.time()
        samples = [
            {"pid": 100, "name": "chrome.exe", "exe": "C:\\chrome.exe", "up_bytes": 5000, "down_bytes": 15000, "timestamp": curr_time}
        ]
        self.db.record_traffic_batch(samples)
        daily = self.db.get_daily_history(days=1)

        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["name"], "chrome.exe")
        self.assertEqual(daily[0]["total_bytes"], 20000)

    def test_timeline_stats(self):
        curr_time = time.time()
        samples = [
            {"pid": 100, "name": "app.exe", "exe": "", "up_bytes": 2048, "down_bytes": 4096, "timestamp": curr_time}
        ]
        self.db.record_traffic_batch(samples)
        timeline = self.db.get_timeline_stats(minutes=5, bucket_seconds=60)

        self.assertGreaterEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["up_bytes"], 2048)
        self.assertEqual(timeline[0]["down_bytes"], 4096)

    def test_cleanup_old_samples(self):
        old_time = time.time() - (20 * 86400) # 20 days ago
        samples = [
            {"pid": 100, "name": "old_app.exe", "exe": "", "up_bytes": 1000, "down_bytes": 1000, "timestamp": old_time}
        ]
        self.db.record_traffic_batch(samples)
        self.db.cleanup_old_samples(retention_days=10)

        top = self.db.get_top_consumers(period_hours=720)
        self.assertEqual(len(top), 0)

if __name__ == "__main__":
    unittest.main()
