import unittest
from unittest.mock import MagicMock
from server import (
    system_info, get_limits, get_top_consumers, get_timeline, get_daily,
    set_limit, remove_limit, LimitRequest, tracker, format_bytes, format_total_bytes,
    qos_manager
)

class TestServerDirectAPI(unittest.TestCase):
    def test_formatting_helpers(self):
        self.assertEqual(format_bytes(500), "500.0 B/s")
        self.assertEqual(format_bytes(2048), "2.0 KB/s")
        self.assertEqual(format_bytes(1024 * 1024 * 5), "5.00 MB/s")

        self.assertEqual(format_total_bytes(500), "500 B")
        self.assertEqual(format_total_bytes(1024 * 1024 * 10), "10.0 MB")

    def test_system_info(self):
        info = system_info()
        self.assertIn("is_admin", info)
        self.assertIn("autostart", info)
        self.assertIn("cpu_count", info)
        self.assertIn("memory_total_gb", info)
        self.assertGreater(info["cpu_count"], 0)

    def test_tracker_snapshot(self):
        snapshot = tracker.get_snapshot()
        self.assertIn("timestamp", snapshot)
        self.assertIn("global", snapshot)
        self.assertIn("processes", snapshot)
        self.assertIn("active_limits", snapshot)

    def test_history_endpoints(self):
        top = get_top_consumers(hours=24, limit=5)
        self.assertIsInstance(top, list)

        timeline = get_timeline(minutes=30)
        self.assertIsInstance(timeline, list)

        daily = get_daily(days=7)
        self.assertIsInstance(daily, list)

    def test_set_and_remove_limit(self):
        qos_manager._run_powershell = MagicMock(return_value=(True, "OK"))

        req = LimitRequest(target="test_browser.exe", app_exe="test_browser.exe", limit_kbps=5120, priority="high")
        res = set_limit(req)
        self.assertEqual(res["status"], "ok")

        limits = get_limits()
        self.assertIn("test_browser.exe", limits)
        self.assertEqual(limits["test_browser.exe"]["kbps"], 5120)

        del_res = remove_limit("test_browser.exe")
        self.assertEqual(del_res["status"], "ok")
        self.assertNotIn("test_browser.exe", get_limits())

if __name__ == "__main__":
    unittest.main()
