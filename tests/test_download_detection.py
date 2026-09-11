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

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_poe2_competing_with_webview2_and_unallocated_traffic(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """PoE 2 with 16 sockets downloading 10.4 MB/s in memory must be attributed ~10 MB/s,
        while WebView2 writing 3 MB/s cache with 0 sockets must receive 0 B/s."""
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=111_080_000, bytes_sent=10_360_000) # 11.08 MB/s down, 360 KB/s up
        ]

        # 16 sockets for PoE 2 (PID 2516)
        conns = []
        for port in range(16):
            c = MagicMock()
            c.pid = 2516
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip='203.133.186.91')
            conns.append(c)

        # 4 sockets for LDPlayer (PID 43552)
        for port in range(4):
            c = MagicMock()
            c.pid = 43552
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip='142.250.190.10')
            conns.append(c)

        # dead TIME_WAIT socket with pid=0 (should NOT trigger unowned remote)
        dead_c = MagicMock()
        dead_c.pid = 0
        dead_c.status = 'TIME_WAIT'
        dead_c.raddr = MagicMock(ip='1.2.3.4')
        conns.append(dead_c)

        mock_net_conns.return_value = conns

        # Processes: PoE 2, LDPlayer, WebView2
        poe_mock = MagicMock()
        poe_mock.info = {
            'pid': 2516,
            'name': 'PathOfExile_KG.exe',
            'exe': 'D:\\Daum Games\\Path of Exile2\\PathOfExile_KG.exe',
            'cpu_percent': 20.3,
            'memory_info': MagicMock(rss=125 * 1024 * 1024)
        }
        ld_mock = MagicMock()
        ld_mock.info = {
            'pid': 43552,
            'name': 'Ld9BoxHeadless.exe',
            'exe': 'C:\\Program Files\\ldplayer\\Ld9BoxHeadless.exe',
            'cpu_percent': 70.0,
            'memory_info': MagicMock(rss=85 * 1024 * 1024)
        }
        wv_mock = MagicMock()
        wv_mock.info = {
            'pid': 35344,
            'name': 'msedgewebview2.exe',
            'exe': 'C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\msedgewebview2.exe',
            'cpu_percent': 21.7,
            'memory_info': MagicMock(rss=146 * 1024 * 1024)
        }

        # Cycle 1
        poe_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=10000)
        ld_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=10000)
        wv_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=10000)
        mock_proc_iter.return_value = [poe_mock, ld_mock, wv_mock]
        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2:
        # - PoE only records 165 KB/s disk writes (buffered in RAM)
        # - LDPlayer records 500 KB/s disk writes
        # - WebView2 writes 3.12 MB/s UI/GPU cache (0 sockets)
        time.sleep(0.02)
        curr_t = time.time()
        self.tracker.prev_proc_io[2516] = (1000, 5000, 10000, curr_t - 1.0)
        self.tracker.prev_proc_io[43552] = (1000, 5000, 10000, curr_t - 1.0)
        self.tracker.prev_proc_io[35344] = (1000, 5000, 10000, curr_t - 1.0)
        self.tracker.prev_time = curr_t - 1.0

        poe_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 165_000, other_bytes=10000)
        ld_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 500_000, other_bytes=10000)
        wv_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 3_120_000, other_bytes=10000)

        snap = self.tracker.get_snapshot()

        poe_proc = next((p for p in snap['processes'] if p['pid'] == 2516), None)
        wv_proc = next((p for p in snap['processes'] if p['pid'] == 35344), None)
        ld_proc = next((p for p in snap['processes'] if p['pid'] == 43552), None)

        self.assertIsNotNone(poe_proc, "PathOfExile_KG.exe must be detected")
        self.assertGreater(poe_proc['down_speed'], 9_500_000, "PoE 2 must capture ~10 MB/s of the download")
        self.assertEqual(poe_proc['connections'], 16)
        self.assertIn("MB/s", poe_proc['down_formatted'])

        if wv_proc:
            self.assertEqual(wv_proc['down_speed'], 0.0, "WebView2 with 0 sockets must receive 0 B/s download")
            self.assertEqual(wv_proc['connections'], 0, "WebView2 must NOT spoof 8 sockets")

        if ld_proc:
            self.assertLess(ld_proc['down_speed'], 2_000_000, "LDPlayer must receive its minor share")

    @patch('psutil.net_io_counters')
    @patch('psutil.net_connections')
    @patch('psutil.process_iter')
    def test_ldplayer_vmdk_writes_do_not_steal_poe2_download(self, mock_proc_iter, mock_net_conns, mock_net_io):
        """
        Real-world user case:
        - Global download: 10.79 MB/s
        - PoE 2 (PID 42356): 19 parallel connections to CDN (203.133.186.91), writing 157 KB/s to disk
        - 3 LDPlayer instances with 62 total connections to diverse IPs, writing 4.27 MB/s to VMDKs
        Verify that PoE 2 captures ~10.7 MB/s and LDPlayer VMDK writes are completely ignored.
        """
        dt = 1.0
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=100_000_000, bytes_sent=10_000_000),
            MagicMock(bytes_recv=110_790_000, bytes_sent=10_050_000) # +10.79 MB down
        ]

        conns = []
        # PoE 2: 19 connections to the same CDN host IP
        for _ in range(19):
            c = MagicMock()
            c.pid = 42356
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip='203.133.186.91')
            conns.append(c)

        # LDPlayer 1: 26 connections scattered across different remote IPs (max 2 per IP)
        for i in range(26):
            c = MagicMock()
            c.pid = 44128
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip=f'172.217.16.{i // 2}')
            conns.append(c)

        # LDPlayer 2: 17 connections scattered (1 per IP)
        for i in range(17):
            c = MagicMock()
            c.pid = 22332
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip=f'142.250.72.{i}')
            conns.append(c)

        # LDPlayer 3: 19 connections scattered (1 per IP)
        for i in range(19):
            c = MagicMock()
            c.pid = 48348
            c.status = 'ESTABLISHED'
            c.raddr = MagicMock(ip=f'157.240.22.{i}')
            conns.append(c)

        mock_net_conns.return_value = conns

        poe_mock = MagicMock()
        poe_mock.info = {
            'pid': 42356,
            'name': 'PathOfExile_KG.exe',
            'exe': 'D:\\Daum Games\\Path of Exile2\\PathOfExile_KG.exe',
            'cpu_percent': 22.3,
            'memory_info': MagicMock(rss=180 * 1024 * 1024)
        }
        ld1_mock = MagicMock()
        ld1_mock.info = {
            'pid': 44128,
            'name': 'Ld9BoxHeadless.exe',
            'exe': 'C:\\LDPlayer\\Ld9BoxHeadless.exe',
            'cpu_percent': 115.4,
            'memory_info': MagicMock(rss=500 * 1024 * 1024)
        }
        ld2_mock = MagicMock()
        ld2_mock.info = {
            'pid': 22332,
            'name': 'Ld9BoxHeadless.exe',
            'exe': 'C:\\LDPlayer\\Ld9BoxHeadless.exe',
            'cpu_percent': 88.9,
            'memory_info': MagicMock(rss=500 * 1024 * 1024)
        }
        ld3_mock = MagicMock()
        ld3_mock.info = {
            'pid': 48348,
            'name': 'Ld9BoxHeadless.exe',
            'exe': 'C:\\LDPlayer\\Ld9BoxHeadless.exe',
            'cpu_percent': 88.7,
            'memory_info': MagicMock(rss=500 * 1024 * 1024)
        }

        # Cycle 1
        poe_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=1000)
        ld1_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=1000)
        ld2_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=1000)
        ld3_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000, other_bytes=1000)
        mock_proc_iter.return_value = [poe_mock, ld1_mock, ld2_mock, ld3_mock]

        self.tracker.prev_time = time.time() - dt
        self.tracker.get_snapshot()

        # Cycle 2:
        curr_t = time.time()
        self.tracker.prev_proc_io[42356] = (1000, 5000, 1000, curr_t - 1.0)
        self.tracker.prev_proc_io[44128] = (1000, 5000, 1000, curr_t - 1.0)
        self.tracker.prev_proc_io[22332] = (1000, 5000, 1000, curr_t - 1.0)
        self.tracker.prev_proc_io[48348] = (1000, 5000, 1000, curr_t - 1.0)
        self.tracker.prev_time = curr_t - 1.0

        # PoE writes only 157 KB/s to disk; LDPlayers write 3.45 MB/s, 589 KB/s, 230 KB/s to VMDKs
        poe_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 157_000, other_bytes=1000)
        ld1_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 3_450_000, other_bytes=1000)
        ld2_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 589_000, other_bytes=1000)
        ld3_mock.io_counters.return_value = MagicMock(read_bytes=1000, write_bytes=5000 + 230_000, other_bytes=1000)

        snap = self.tracker.get_snapshot()

        poe_proc = next((p for p in snap['processes'] if p['pid'] == 42356), None)
        ld1_proc = next((p for p in snap['processes'] if p['pid'] == 44128), None)
        ld2_proc = next((p for p in snap['processes'] if p['pid'] == 22332), None)
        ld3_proc = next((p for p in snap['processes'] if p['pid'] == 48348), None)

        self.assertIsNotNone(poe_proc, "PathOfExile_KG.exe must be found")
        # PoE 2 should capture the entire 10.79 MB/s download!
        self.assertGreater(poe_proc['down_speed'], 10_000_000, "PoE 2 must capture ~10.79 MB/s")
        self.assertEqual(poe_proc['connections'], 19)

        # None of the LDPlayer instances should receive network download attribution from their VMDK writes
        if ld1_proc:
            self.assertEqual(ld1_proc['down_speed'], 0.0, "LDPlayer VMDK writes must NOT be attributed network download")
        if ld2_proc:
            self.assertEqual(ld2_proc['down_speed'], 0.0, "LDPlayer VMDK writes must NOT be attributed network download")
        if ld3_proc:
            self.assertEqual(ld3_proc['down_speed'], 0.0, "LDPlayer VMDK writes must NOT be attributed network download")

if __name__ == '__main__':
    unittest.main()
