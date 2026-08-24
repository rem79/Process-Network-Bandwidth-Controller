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

        # Remove
        success, msg = manager.remove_limit("test_app.exe", save_state=False)
        self.assertTrue(success)
        self.assertNotIn("test_app.exe", manager.get_all_limits())

if __name__ == "__main__":
    unittest.main()
