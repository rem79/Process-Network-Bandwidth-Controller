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

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_user_mode_elevated_process_download_with_masked_pid(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """Simulate an elevated game patcher running in User Mode where Windows returns conn.pid = None."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=111_000_000, bytes_sent=10_050_000) # +11 MB down
        ]

        # Windows User Mode TCP table: socket has pid=None (masked)
        masked_conn = MagicMock()
        masked_conn.pid = None
        masked_conn.status = 'ESTABLISHED'
        masked_conn.raddr = MagicMock(ip='203.133.186.91') # Kakao/PoE server
        mock_net_conns.return_value = [masked_conn]

        # Elevated PoE Game Client (PathOfExile_x64_KG.exe)
        proc_mock = MagicMock()
        proc_mock.info = {
            'pid': 40732,
            'name': 'PathOfExile_x64_KG.exe',
            'exe': 'D:\\Daum Games\\Path of Exile2\\PathOfExile_x64_KG.exe',
            'cpu_percent': 12.0,
            'memory_info': MagicMock(rss=800 * 1024 * 1024)
        }

        # Cycle 1
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000)
        mock_proc_iter.return_value = [proc_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2: +11 MB written to disk over 1.0 second
        time.sleep(0.02) # Ensure positive elapsed time
        curr_t = time.time()
        # Seed prev_proc_io timestamp to exactly 1.0s before curr_t
        self.tracker.prev_proc_io[40732] = (1000, 5000, curr_t - 1.0)
        self.tracker.prev_time = curr_t - 1.0
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 11_000_000)
        snap = self.tracker.get_snapshot()

        poe_proc = next((p for p in snap['processes'] if p['pid'] == 40732), None)
        self.assertIsNotNone(poe_proc, "Elevated game client must be detected even with masked PID")
        self.assertGreater(poe_proc['down_speed'], 9_500_000, "Download speed should capture ~11 MB/s")
        self.assertGreaterEqual(poe_proc['connections'], 1, "Should indicate active socket stream")
        self.assertIn("MB/s", poe_proc['down_formatted'])

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_winsock_other_bytes_download_attribution(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """Simulate PoE 2 downloading via Winsock AFD/IOCTLs (other_bytes) into memory-mapped file."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=110_600_000, bytes_sent=10_050_000) # +10.6 MB down
        ]

        # Windows User Mode TCP table: socket has pid=None (masked)
        masked_conn = MagicMock()
        masked_conn.pid = None
        masked_conn.status = 'ESTABLISHED'
        masked_conn.raddr = MagicMock(ip='203.133.186.91')
        mock_net_conns.return_value = [masked_conn]

        proc_mock = MagicMock()
        proc_mock.info = {
            'pid': 24464,
            'name': 'Client.exe',
            'exe': 'D:\\Daum Games\\Path of Exile2\\Client.exe',
            'cpu_percent': 18.0,
            'memory_info': MagicMock(rss=1200 * 1024 * 1024)
        }

        # Cycle 1
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=10000)
        mock_proc_iter.return_value = [proc_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2: +10.6 MB accumulated exclusively in other_bytes (Winsock IOCTLs)
        time.sleep(0.02)
        curr_t = time.time()
        self.tracker.prev_proc_io[24464] = (1000, 5000, 10000, curr_t - 1.0)
        self.tracker.prev_time = curr_t - 1.0
        proc_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=10000 + 10_600_000)
        snap = self.tracker.get_snapshot()

        poe_proc = next((p for p in snap['processes'] if p['pid'] == 24464), None)
        self.assertIsNotNone(poe_proc, "PoE 2 Client.exe must be detected via other_bytes")
        self.assertGreater(poe_proc['down_speed'], 9_000_000, "Download speed should be ~10.6 MB/s")
        self.assertIn("MB/s", poe_proc['down_formatted'])

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_loopback_only_msedgewebview2_not_attributed_download(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """msedgewebview2.exe connected only to 127.0.0.1 must NOT steal internet download traffic even if writing cache to disk."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=110_000_000, bytes_sent=10_050_000) # 10 MB system download
        ]

        # Loopback connection only (127.0.0.1)
        loopback_conn = MagicMock()
        loopback_conn.pid = 13468
        loopback_conn.status = 'ESTABLISHED'
        loopback_conn.raddr = MagicMock(ip='127.0.0.1')
        mock_net_conns.return_value = [loopback_conn]

        wv_mock = MagicMock()
        wv_mock.info = {
            'pid': 13468,
            'name': 'msedgewebview2.exe',
            'exe': 'C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\msedgewebview2.exe',
            'cpu_percent': 2.0,
            'memory_info': MagicMock(rss=100 * 1024 * 1024)
        }

        # Cycle 1
        wv_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=1000)
        mock_proc_iter.return_value = [wv_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2: WebView2 writes 3 MB of DOM/canvas cache to local disk
        wv_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 3_000_000, other_bytes=1000)
        self.tracker.prev_time = time.time() - dt
        snap = self.tracker.get_snapshot()

        wv_proc = next((p for p in snap['processes'] if p['pid'] == 13468), None)
        if wv_proc:
            self.assertEqual(wv_proc['down_speed'], 0.0, "Loopback WebView2 must not be attributed internet download")
            self.assertEqual(wv_proc['up_speed'], 0.0)

if __name__ == '__main__':
    unittest.main()
