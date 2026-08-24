import sys
import os
import ctypes
import threading
import time
import multiprocessing
import logging
from PIL import Image, ImageDraw
import pystray
import webview

import autostart_manager

# Setup Logging in AppData
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AntigravityNetworkSentinel')
os.makedirs(APPDATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(APPDATA_DIR, "desktop.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.info("Desktop Sentinel App Starting...")

# Global Window Handle
app_window = None
tray_icon = None


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_admin():
    """
    Relaunches the current script/exe with Administrator privileges via Windows UAC prompt.
    """
    if not is_admin():
        print("Requesting Administrator privileges (UAC)...")
        try:
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                params = ""
            else:
                executable = sys.executable
                params = f'"{os.path.abspath(__file__)}"'

            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", executable, params, None, 1
            )
            if ret > 32:
                sys.exit(0)
            else:
                print(f"UAC elevation refused or failed with code {ret}")
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")

def run_server():
    try:
        import uvicorn
        from server import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
    except Exception as e:
        logging.error(f"Error running uvicorn server: {e}", exc_info=True)

def create_tray_image():
    """
    Creates a dynamic high-tech network icon in memory using PIL.
    """
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), (7, 10, 18, 255))
    dc = ImageDraw.Draw(image)
    
    # Outer Glow Cyan Ring
    dc.ellipse([6, 6, 58, 58], outline=(0, 242, 254, 255), width=4)
    # Inner Cyber Violet Circle
    dc.ellipse([18, 18, 46, 46], fill=(157, 78, 221, 255))
    # Center Pulse Dot
    dc.ellipse([26, 26, 38, 38], fill=(0, 245, 212, 255))

    return image

def show_window(icon=None, item=None):
    global app_window
    if app_window:
        try:
            app_window.show()
            app_window.restore()
        except Exception as e:
            logging.error(f"Error restoring window: {e}")

def toggle_autostart_menu(icon=None, item=None):
    current = autostart_manager.is_autostart_enabled()
    autostart_manager.set_autostart(not current)

def is_autostart_checked(item):
    return autostart_manager.is_autostart_enabled()

def quit_app(icon=None, item=None):
    global tray_icon
    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass
    os._exit(0)

def on_closing():
    """
    When user clicks [X] on window, hide to System Tray instead of exiting.
    """
    global app_window
    if app_window:
        app_window.hide()
    return False # Cancel default close to keep app running in tray

def setup_tray():
    global tray_icon
    try:
        menu = pystray.Menu(
            pystray.MenuItem("👁 Open Controller Dashboard", show_window, default=True),
            pystray.MenuItem("🔄 Run on Windows Boot", toggle_autostart_menu, checked=is_autostart_checked),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit Controller", quit_app)
        )

        image = create_tray_image()
        tray_icon = pystray.Icon("ProcessNetworkBandwidthController", image, "Process Network Bandwidth Controller", menu)
        tray_icon.run()
    except Exception as e:
        logging.error(f"Error starting tray icon: {e}", exc_info=True)

def main():
    global app_window

    # 1. Force Administrator privileges
    elevate_admin()

    logging.info("Starting background FastAPI server thread...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    logging.info("Starting background System Tray thread...")
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    time.sleep(1.0)

    logging.info("Creating PyWebView desktop window...")
    app_window = webview.create_window(
        title="Process Network Bandwidth Controller",
        url="http://127.0.0.1:8000",
        width=1340,
        height=880,
        min_size=(1024, 700),
        resizable=True,
        text_select=True
    )

    app_window.events.closing += on_closing

    logging.info("Starting PyWebView event loop...")
    webview.start(private_mode=False)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

