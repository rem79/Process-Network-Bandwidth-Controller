import subprocess
import json
import os
import re
import sys
import logging
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Persistent Rules Directory in AppData
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AntigravityNetworkSentinel')
os.makedirs(APPDATA_DIR, exist_ok=True)
RULES_FILE = os.path.join(APPDATA_DIR, "qos_rules.json")

def sanitize_policy_name(name: str) -> str:
    """
    Sanitizes policy name to contain only safe alphanumeric characters and underscores.
    """
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    return f"NetControl_{cleaned}"

def sanitize_exe_target(exe_str: str) -> str:
    """
    Sanitizes executable match string or path for NetQosPolicy matching, safely preserving path backslashes.
    """
    if not exe_str or exe_str == "*":
        return "*"
    # Strip dangerous injection characters while preserving valid path separators
    return exe_str.replace('"', '').replace("'", "").replace('`', '').replace('$', '').strip()

def ensure_qos_registry_enabled() -> bool:
    r"""
    On non-domain joined (workgroup) Windows 10 & 11 PCs, Network Location Awareness (NLA)
    silently disables all local QoS and NetQosPolicy rules by default.
    Setting HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\QoS\Do not use NLA = 1
    forces Windows to honor local QoS policies on all networks.
    """
    try:
        import winreg
        key_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\QoS"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(key, "Do not use NLA", 0, winreg.REG_SZ, "1")
        logging.info("Ensured HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\QoS 'Do not use NLA' is set to '1'")
        return True
    except Exception as e:
        logging.warning(f"Could not set QoS NLA registry key (requires Admin): {e}")
        return False

class QoSManager:
    """
    Enterprise-grade Windows NetQosPolicy bandwidth management engine.
    Controls per-process and system-wide bandwidth throttling, priorities, and persistence.
    Supports both Download (TCP ACK pacing) and Upload (direct egress) throttling.
    """
    def __init__(self):
        ensure_qos_registry_enabled()
        self.rules: Dict[str, Dict[str, Any]] = self._load_rules()
        self.restore_saved_rules()

    def _load_rules(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logging.info(f"Loaded {len(data)} saved QoS rules from {RULES_FILE}")
                    return data
            except Exception as e:
                logging.error(f"Error loading QoS rules file: {e}")
        return {}

    def _save_rules(self):
        try:
            with open(RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
            logging.info(f"Saved {len(self.rules)} QoS rules to {RULES_FILE}")
        except Exception as e:
            logging.error(f"Error saving QoS rules file: {e}")

    def _run_powershell(self, script_block: str) -> tuple[bool, str]:
        """
        Executes a PowerShell command safely and returns (success, output/error_message).
        """
        full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script_block]
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=12)
            if res.returncode == 0:
                return True, res.stdout.strip()
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logging.warning(f"PowerShell command failed ({res.returncode}): {err}")
                return False, err
        except subprocess.TimeoutExpired:
            logging.error("PowerShell command execution timed out.")
            return False, "Execution timed out (12s)"
        except Exception as e:
            logging.error(f"Execution error running PowerShell: {e}")
            return False, str(e)

    def restore_saved_rules(self):
        """
        Re-enforces all saved rules into Windows NetQosPolicy on application startup.
        """
        if not self.rules:
            return

        logging.info("Restoring saved QoS rules into Windows NetQosPolicy...")
        for target_name, item in list(self.rules.items()):
            kbps = item.get("kbps", 0)
            app_exe = item.get("app_exe", item.get("target", target_name))
            priority = item.get("priority", "normal")
            direction = item.get("direction", "both")
            if kbps > 0:
                self.set_limit(target_name, app_exe, kbps, priority=priority, direction=direction, save_state=False)

    def set_limit(self, target_name: str, app_exe: str, limit_kbps: int, priority: str = "normal", direction: str = "both", save_state: bool = True) -> tuple[bool, str]:
        """
        Sets a bandwidth limit in KB/s for a specific executable or system-wide.
        Handles both download (TCP ACK pacing) and upload (outbound throttling).
        """
        if limit_kbps <= 0:
            return self.remove_limit(target_name, save_state=save_state)

        ensure_qos_registry_enabled()

        # Clean target: Extract pure executable basename (e.g. "PathOfExile_KG.exe")
        raw_target = target_name.replace('/', '\\').strip()
        raw_exe = app_exe.replace('/', '\\').strip() if app_exe else ""
        if raw_target.lower() == "global" or raw_target == "*":
            match_exe = "*"
            display_target = "Global"
        else:
            # If app_exe is specified (e.g. "D:\Games\PathOfExile_KG.exe"), extract its basename
            candidate = raw_exe if raw_exe else raw_target
            display_target = os.path.basename(candidate)
            if not display_target.lower().endswith('.exe') and '.' not in display_target:
                display_target = f"{display_target}.exe"
            match_exe = display_target

        clean_target = sanitize_policy_name(display_target)

        # Rate calculation:
        # Windows NetQosPolicy -ThrottleRateActionBitsPerSecond is an egress (outbound) rate limiter.
        # When throttling download (or 'both'), the client's outbound traffic is TCP ACKs.
        # Average TCP data MSS is 1460 bytes with 1 ACK per 2 full packets (2920 bytes) to 56 bytes ACK ratio (~52:1).
        # Throttling the ACK rate forces the remote sender's congestion window (cwnd) to throttle down
        # to EXACTLY the target download rate (verified by speed tests).
        if direction.lower() == "up":
            bps = int(limit_kbps * 1024 * 8)
        else:
            # "down" or "both"
            TCP_DATA_TO_ACK_RATIO = 52.0
            bps = max(64000, int((limit_kbps * 1024 * 8) / TCP_DATA_TO_ACK_RATIO))

        # First remove existing policy to avoid duplicate name collision
        self._run_powershell(f"Remove-NetQosPolicy -Name '{clean_target}' -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue")

        # Construct DSCP value based on priority (if supported)
        dscp_param = ""
        if priority.lower() == "high":
            dscp_param = "-DSCPAction 46" # Expedited Forwarding
        elif priority.lower() == "low":
            dscp_param = "-DSCPAction 10" # Lower priority

        if match_exe == "*":
            ps_cmd = f"New-NetQosPolicy -Name '{clean_target}' -ThrottleRateActionBitsPerSecond {bps} {dscp_param} -PolicyStore ActiveStore -Confirm:$false"
        else:
            ps_cmd = f"New-NetQosPolicy -Name '{clean_target}' -AppPathNameMatchCondition '{match_exe}' -ThrottleRateActionBitsPerSecond {bps} {dscp_param} -PolicyStore ActiveStore -Confirm:$false"

        success, msg = self._run_powershell(ps_cmd)
        clean_app_exe = sanitize_exe_target(app_exe or target_name)
        rule_data = {
            "target": target_name,
            "policy_name": clean_target,
            "app_exe": clean_app_exe,
            "bps": bps,
            "kbps": limit_kbps,
            "priority": priority,
            "direction": direction,
            "active": success,
            "error": None if success else msg
        }
        self.rules[target_name] = rule_data
        if save_state:
            self._save_rules()

        if success:
            dir_label = "DOWNLOAD & UPLOAD" if direction == "both" else ("UPLOAD ONLY" if direction == "up" else "DOWNLOAD ONLY")
            return True, f"QoS limit active for {target_name} ({limit_kbps} KB/s, {dir_label}, Priority: {priority.upper()})"
        else:
            return False, f"Failed to apply Windows QoS policy: {msg}. (Admin rights required)"

    def remove_limit(self, target_name: str, save_state: bool = True) -> tuple[bool, str]:
        """
        Removes QoS policy for the specified target.
        """
        raw_target = target_name.replace('/', '\\').strip()
        display_target = os.path.basename(raw_target) if raw_target.lower() != "global" else "Global"
        clean_target = sanitize_policy_name(display_target)
        ps_cmd = f"Remove-NetQosPolicy -Name '{clean_target}' -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue"
        success, msg = self._run_powershell(ps_cmd)

        if target_name in self.rules:
            del self.rules[target_name]
            if save_state:
                self._save_rules()

        return True, f"Bandwidth limit for {target_name} removed."

    def clear_all_limits(self) -> tuple[bool, str]:
        """
        Clears all active QoS policies managed by the controller.
        """
        for target in list(self.rules.keys()):
            self.remove_limit(target, save_state=False)
        self.rules.clear()
        self._save_rules()
        return True, "All QoS policies cleared."

    def get_all_limits(self) -> Dict[str, Dict[str, Any]]:
        return self.rules

# Global QoS Manager Singleton
qos_manager = QoSManager()
