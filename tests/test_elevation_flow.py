import unittest
from unittest.mock import patch, MagicMock
import sys
import os

import main_desktop

class TestElevationFlow(unittest.TestCase):
    def test_request_self_elevation_success(self):
        with patch.object(main_desktop.ctypes.windll.shell32, "ShellExecuteW", return_value=42):
            res = main_desktop.request_self_elevation()
            self.assertTrue(res)

    def test_request_self_elevation_cancelled(self):
        # ShellExecute returns <= 32 on error or cancellation
        with patch.object(main_desktop.ctypes.windll.shell32, "ShellExecuteW", return_value=5):
            res = main_desktop.request_self_elevation()
            self.assertFalse(res)

    def test_request_self_elevation_exception(self):
        with patch.object(main_desktop.ctypes.windll.shell32, "ShellExecuteW", side_effect=RuntimeError("OS Error")):
            res = main_desktop.request_self_elevation()
            self.assertFalse(res)

    def test_prompt_user_mode_fallback_yes(self):
        # IDYES = 6
        with patch.object(main_desktop.ctypes.windll.user32, "MessageBoxW", return_value=6):
            res = main_desktop.prompt_user_mode_fallback()
            self.assertTrue(res)

    def test_prompt_user_mode_fallback_no(self):
        # IDNO = 7
        with patch.object(main_desktop.ctypes.windll.user32, "MessageBoxW", return_value=7):
            res = main_desktop.prompt_user_mode_fallback()
            self.assertFalse(res)

if __name__ == "__main__":
    unittest.main()
