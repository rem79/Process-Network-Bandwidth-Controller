import unittest
from unittest.mock import MagicMock, patch
import time
from server import ProcessTracker

class TestDownloadDetection(unittest.TestCase):
    def setUp(self):
        self.tracker = ProcessTracker()

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_high_bandwidth_file_download_attribution(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """Simulate a game patcher downloading at 10 MB/s and writing chunks to disk."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=110_000_000, bytes_sent=10_050_000)
        ]

        mock_conn = MagicMock()
        mock_conn.pid = 5555
        mock_conn.status = 'ESTABLISHED'
        mock_conn.raddr = MagicMock(ip='198.51.100.25')
        mock_net_conns.return_value = [mock_conn]

        proc_mock = MagicMock()
        proc_mock.info = {
            'pid': 5555,
            'name': 'PathOfExile.exe',
            'exe': 'C:\\Games\\PoE\\PathOfExile.exe',
            'cpu_percent': 15.0,
            'memory_info': MagicMock(rss=500 * 1024 * 1024)
        }
        
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000)
        mock_proc_iter.return_value = [proc_mock]
        
        self.tracker.prev_time = time.time() - dt
        snap1 = self.tracker.get_snapshot()

        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 10_000_000)
        self.tracker.prev_time = time.time() - dt
        snap2 = self.tracker.get_snapshot()

        poe_proc = next((p for p in snap2['processes'] if p['pid'] == 5555), None)
        self.assertIsNotNone(poe_proc, "PathOfExile.exe should be present in process list")
        self.assertGreater(poe_proc['down_speed'], 9_000_000, "Download speed should be ~10 MB/s")
        self.assertLess(poe_proc['up_speed'], 100_000, "Upload speed should be small (ACKs)")
        self.assertIn("MB/s", poe_proc['down_formatted'])

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_local_disk_copy_without_network_not_attributed(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """Processes doing local file copies with 0 connections must NOT be attributed network traffic."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000, bytes_sent=50_000),
            MagicMock(bytes_recv=100_000, bytes_sent=50_000)
        ]
        mock_net_conns.return_value = []

        proc_mock = MagicMock()
        proc_mock.info = {
            'pid': 8888,
            'name': '7zG.exe',
            'exe': 'C:\\Program Files\\7-Zip\\7zG.exe',
            'cpu_percent': 90.0,
            'memory_info': MagicMock(rss=200 * 1024 * 1024)
        }
        
        proc_mock.io_counters.return_value = MagicMock(read_bytes=0, write_bytes=0)
        mock_proc_iter.return_value = [proc_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        proc_mock.io_counters.return_value = MagicMock(read_bytes=500_000_000, write_bytes=500_000_000)
        self.tracker.prev_time = time.time() - dt
        snap = self.tracker.get_snapshot()

        seven_zip = next((p for p in snap['processes'] if p['pid'] == 8888), None)
        if seven_zip:
            self.assertEqual(seven_zip['down_speed'], 0.0)
            self.assertEqual(seven_zip['up_speed'], 0.0)

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_high_bandwidth_file_upload_attribution(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """Simulate browser uploading a file to cloud at 10 MB/s, reading from disk."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=10_000_000, bytes_sent=100_000_000),
            MagicMock(bytes_recv=10_050_000, bytes_sent=110_000_000) # +50 KB down, +10 MB up
        ]

        mock_conn = MagicMock()
        mock_conn.pid = 7777
        mock_conn.status = 'ESTABLISHED'
        mock_conn.raddr = MagicMock(ip='142.250.190.46') # Google Drive IP
        mock_net_conns.return_value = [mock_conn]

        proc_mock = MagicMock()
        proc_mock.info = {
            'pid': 7777,
            'name': 'chrome.exe',
            'exe': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            'cpu_percent': 20.0,
            'memory_info': MagicMock(rss=400 * 1024 * 1024)
        }
        
        # Cycle 1
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000)
        mock_proc_iter.return_value = [proc_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2: +10 MB read from disk to upload
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000 + 10_000_000, write_bytes=5000)
        self.tracker.prev_time = time.time() - dt
        snap = self.tracker.get_snapshot()

        chrome_proc = next((p for p in snap['processes'] if p['pid'] == 7777), None)
        self.assertIsNotNone(chrome_proc, "chrome.exe should be present in process list")
        self.assertGreater(chrome_proc['up_speed'], 9_000_000, "Upload speed should be ~10 MB/s")
        self.assertLess(chrome_proc['down_speed'], 100_000, "Download speed should be small (ACKs)")
        self.assertIn("MB/s", chrome_proc['up_formatted'])

if __name__ == '__main__':
    unittest.main()
