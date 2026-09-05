import subprocess
import os
import sys
import webview
import clr_loader

def build():
    print("==================================================")
    print("Building Single Standalone Executable (NetworkSentinelApp.exe - OneFile Mode)")
    print("==================================================")

    webview_dir = os.path.dirname(webview.__file__)
    clr_dir = os.path.dirname(clr_loader.__file__)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "history_db",
        "--hidden-import", "sqlite3",
        "--hidden-import", "network_inspector",
        "--hidden-import", "diagnostics",
        "--collect-all", "webview",
        "--collect-all", "clr_loader",
        "--add-data", f"{webview_dir};webview",
        "--add-data", f"{clr_dir};clr_loader",
        "--add-data", "static;static",
        "--add-data", "qos_rules.json;.",
        "--name", "NetworkSentinelApp",
        "main_desktop.py"
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    if res.returncode == 0:
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist", "NetworkSentinelApp.exe"))
        print("\n[SUCCESS] Compiled single standalone executable successfully!")
        print(f"Single EXE Location: {exe_path}")
        print("You can copy this single .exe file to any Windows computer and run it directly!")
    else:
        print("\n[ERROR] Build failed.")

if __name__ == "__main__":
    build()

