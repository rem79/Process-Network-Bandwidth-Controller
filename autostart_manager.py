import winreg
import sys
import os
import logging

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ProcessNetworkBandwidthController"

def get_target_command() -> str:
    if getattr(sys, 'frozen', False):
        # Compiled PyInstaller EXE path
        return f'"{sys.executable}"'
    else:
        # Running from Python source
        desktop_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main_desktop.py"))
        return f'"{sys.executable}" "{desktop_script}"'

def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Error reading autostart registry: {e}")
        return False

def set_autostart(enable: bool) -> tuple[bool, str]:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        if enable:
            cmd = get_target_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logging.info(f"Registry autostart enabled: {cmd}")
            return True, "Registered for automatic startup on Windows boot."
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            logging.info("Registry autostart disabled.")
            return True, "Removed from Windows boot startup."
    except Exception as e:
        logging.error(f"Error setting autostart registry: {e}")
        return False, str(e)
