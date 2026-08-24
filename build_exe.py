import subprocess
import os
import sys
import webview
import clr_loader

def build():
    print("==================================================")
    print("Building Standalone Process Network Bandwidth Controller.exe (v2.0)")
    print("==================================================")

    webview_dir = os.path.dirname(webview.__file__)
    clr_dir = os.path.dirname(clr_loader.__file__)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--uac-admin",  # Forces Windows Administrator privilege prompt
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "history_db",
        "--hidden-import", "sqlite3",
        "--collect-all", "webview",
        "--collect-all", "clr_loader",
        "--add-data", f"{webview_dir};webview",
        "--add-data", f"{clr_dir};clr_loader",
        "--add-data", "static;static",
        "--add-data", "qos_rules.json;.",
        "--name", "Process Network Bandwidth Controller",
        "main_desktop.py"
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    if res.returncode == 0:
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist", "Process Network Bandwidth Controller", "Process Network Bandwidth Controller.exe"))
        print("\n[SUCCESS] Compiled standalone executable successfully!")
        print(f"EXE Location: {exe_path}")
    else:
        print("\n[ERROR] Build failed.")

if __name__ == "__main__":
    build()
