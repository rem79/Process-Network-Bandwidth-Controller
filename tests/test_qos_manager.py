import unittest
from unittest.mock import MagicMock
from qos_manager import QoSManager, sanitize_policy_name, sanitize_exe_target

class TestQoSManager(unittest.TestCase):
    def test_sanitize_policy_name(self):
        self.assertEqual(sanitize_policy_name("chrome.exe"), "NetControl_chrome.exe")
        self.assertEqual(sanitize_policy_name("app; rm -rf /"), "NetControl_app__rm_-rf__")
        self.assertEqual(sanitize_policy_name("my_custom_app 123"), "NetControl_my_custom_app_123")

    def test_sanitize_exe_target(self):
        self.assertEqual(sanitize_exe_target('C:\\Program Files\\app.exe'), 'C:\\Program Files\\app.exe')
        self.assertEqual(sanitize_exe_target('app.exe" ; evil_cmd `'), 'app.exe ; evil_cmd')

    def test_qos_manager_in_memory_rules(self):
        manager = QoSManager()
        manager._run_powershell = MagicMock(return_value=(True, "OK"))

        success, msg = manager.set_limit("test_app.exe", "test_app.exe", 2048, priority="high", save_state=False)
        self.assertTrue(success)
        rules = manager.get_all_limits()
        self.assertIn("test_app.exe", rules)
        self.assertEqual(rules["test_app.exe"]["kbps"], 2048)
        self.assertEqual(rules["test_app.exe"]["priority"], "high")

        # Test direction and ACK pacing calculation
        manager._run_powershell.reset_mock()
        success, msg = manager.set_limit("poe.exe", r"D:\Games\PoE\PathOfExile_KG.exe", 1024, direction="down", save_state=False)
        self.assertTrue(success)
        self.assertIn("poe.exe", manager.get_all_limits())
        self.assertEqual(manager.get_all_limits()["poe.exe"]["direction"], "down")
        # Verify that match condition stripped path to basename
        ps_call = manager._run_powershell.call_args[0][0]
        self.assertIn("-AppPathNameMatchCondition 'PathOfExile_KG.exe'", ps_call)
        # Verify ACK pacing rate: (1024 * 1024 * 8) / 52.0 = 161319 bps
        expected_ack_bps = int((1024 * 1024 * 8) / 52.0)
        self.assertIn(f"-ThrottleRateActionBitsPerSecond {expected_ack_bps}", ps_call)

        # Test upload rate (direct bps)
        manager._run_powershell.reset_mock()
        success, msg = manager.set_limit("poe.exe", "poe.exe", 1024, direction="up", save_state=False)
        self.assertTrue(success)
        ps_call_up = manager._run_powershell.call_args[0][0]
        self.assertIn(f"-ThrottleRateActionBitsPerSecond {1024 * 1024 * 8}", ps_call_up)

        # Remove
        success, msg = manager.remove_limit("test_app.exe", save_state=False)
        self.assertTrue(success)
        self.assertNotIn("test_app.exe", manager.get_all_limits())

if __name__ == "__main__":
    unittest.main()
