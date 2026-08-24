"""
Unit tests for Next-Gen Network Sentinel Suite v3.0 (Inspector & Diagnostics)
"""

import unittest
import os
from unittest.mock import patch, MagicMock
import network_inspector
import diagnostics
import server

class TestV3Suite(unittest.TestCase):
    def test_geoip_and_rdns(self):
        # 1. Private IP
        geo_local = network_inspector.resolve_geoip_sync("192.168.1.1")
        self.assertEqual(geo_local["country"], "Local")
        self.assertEqual(geo_local["flag"], "🏠")

        # 2. Known CDN / Cloud range
        geo_netflix = network_inspector.resolve_geoip_sync("207.65.34.76")
        self.assertEqual(geo_netflix["country"], "US")
        self.assertIn("Netflix", geo_netflix["org"])

        # 3. Korea Netflix OpenConnect
        geo_kr = network_inspector.resolve_geoip_sync("183.91.238.210")
        self.assertEqual(geo_kr["country"], "KR")
        self.assertEqual(geo_kr["flag"], "🇰🇷")

    def test_threat_heuristics(self):
        # Normal port 443
        threat_normal = network_inspector.inspect_threat("142.250.1.1", 443, "chrome.exe")
        self.assertEqual(threat_normal["level"], "safe")

        # Suspicious Metasploit port 4444
        threat_suspicious = network_inspector.inspect_threat("1.2.3.4", 4444, "unknown.exe")
        self.assertEqual(threat_suspicious["level"], "danger")
        self.assertEqual(threat_suspicious["badge"], "THREAT_SUSPICIOUS")

    def test_latency_measurement(self):
        # Localhost latency
        lat = network_inspector.measure_latency_ms_sync("127.0.0.1", 80)
        self.assertIsInstance(lat, float)
        self.assertGreaterEqual(lat, 0.0)

    def test_nslookup_benchmark(self):
        res = diagnostics.run_nslookup("google.com")
        self.assertEqual(res["domain"], "google.com")
        self.assertTrue(len(res["benchmarks"]) > 0)
        self.assertIn("fastest_dns", res)

    def test_traceroute_engine(self):
        # Fast mocked traceroute parsing test
        mock_output = "Tracing route to 8.8.8.8 over a maximum of 3 hops\n  1     1 ms     1 ms     1 ms  192.168.155.1\n  2     8 ms     7 ms     8 ms  168.126.63.1\n"
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = mock_output
            mock_run.return_value = mock_proc
            
            res = diagnostics.run_visual_traceroute("8.8.8.8", max_hops=2)
            self.assertEqual(res["target"], "8.8.8.8")
            self.assertEqual(len(res["hops"]), 2)
            self.assertEqual(res["hops"][0]["hop"], 1)
            self.assertEqual(res["hops"][0]["ip"], "192.168.155.1")

    def test_wifi_lan_health(self):
        health = diagnostics.get_wifi_lan_health()
        self.assertIn("interface", health)
        self.assertIn("signal_pct", health)
        self.assertIn("diagnosis", health)

    def test_server_v3_direct_endpoints(self):
        # Health endpoint
        res_health = server.health_endpoint()
        self.assertIn("signal_pct", res_health)

        # nslookup endpoint
        req_ns = server.NslookupRequest(domain="netflix.com")
        res_ns = server.nslookup_endpoint(req_ns)
        self.assertEqual(res_ns["domain"], "netflix.com")

        # Port Test endpoint
        req_port = server.PortTestRequest(host="127.0.0.1", port=80)
        res_port = server.port_test_endpoint(req_port)
        self.assertIn("status", res_port)
        self.assertIn("service", res_port)

        # Ping sample endpoint
        req_ping = server.PingSampleRequest(host="8.8.8.8")
        res_ping = server.ping_sample_endpoint(req_ping)
        self.assertIn("status", res_ping)

        # Export Report endpoint
        req_export = server.ExportReportRequest(html_content="<h1>Test</h1>", filename="test_report_sample.html")
        res_export = server.export_report_endpoint(req_export)
        self.assertEqual(res_export["status"], "ok")
        if os.path.exists(res_export["file_path"]):
            os.remove(res_export["file_path"])

    def test_port_tester_standalone(self):
        res = diagnostics.test_tcp_port("127.0.0.1", 80, timeout=0.5)
        self.assertIn("status", res)
        self.assertIn("host", res)

    def test_network_flush_standalone(self):
        res = diagnostics.flush_network_stack()
        self.assertEqual(res["status"], "ok")
        self.assertIn("actions", res)

if __name__ == "__main__":
    unittest.main()
