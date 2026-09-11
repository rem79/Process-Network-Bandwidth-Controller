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

# Determine if running with Administrator privileges
is_admin_mode = False
try:
    is_admin_mode = ctypes.windll.shell32.IsUserAnAdmin() != 0
except Exception:
    pass

# Isolate WebView2 User Data Folder into separate Admin vs User caches to prevent ACL/lock collisions
cache_folder_name = "WebView2_Admin_Cache" if is_admin_mode else "WebView2_User_Cache"
WEBVIEW2_CACHE_DIR = os.path.join(APPDATA_DIR, cache_folder_name)
os.makedirs(WEBVIEW2_CACHE_DIR, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = WEBVIEW2_CACHE_DIR

# Critical Chromium / WebView2 flags:
# When running elevated as Administrator on Windows 10/11, Chromium's GPU hardware acceleration
# and LowIL sandbox trigger D3D11 compositor device loss and watchdog crashes, leading to a black screen.
# Disabling GPU hardware acceleration and sandbox restrictions ensures 100% stable, crash-free rendering.
browser_args = [
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--disable-software-rasterizer",
    "--no-sandbox",
    "--disable-features=ElasticOverscroll,msSmartScreenProtection",
    "--disable-dev-shm-usage",
    "--allow-insecure-localhost"
]
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = " ".join(browser_args)

# Monkey-patch pywebview's EdgeChrome creation properties to inject the anti-black-screen arguments
try:
    import webview.platforms.edgechromium as ec
    from webview import settings as webview_settings
    from webview.platforms.edgechromium import (
        WebView2, CoreWebView2CreationProperties, Color, WinForms, Semaphore,
        TaskScheduler, DEFAULT_HTML, _state, get_app_root
    )

    def patched_edge_init(self, form, window, cache_dir):
        self.pywebview_window = window
        self.webview = WebView2()
        props = CoreWebView2CreationProperties()

        runtime_path = webview_settings.get('WEBVIEW2_RUNTIME_PATH')
        if runtime_path:
            if not os.path.isabs(runtime_path):
                runtime_path = os.path.join(get_app_root(), runtime_path)
            if os.path.exists(runtime_path):
                props.BrowserExecutableFolder = runtime_path

        props.UserDataFolder = cache_dir or WEBVIEW2_CACHE_DIR
        self.user_data_folder = props.UserDataFolder
        props.set_IsInPrivateModeEnabled(_state.get('private_mode', False))

        # Explicitly set all anti-black-screen arguments
        extra_args = [
            '--disable-features=ElasticOverscroll,msSmartScreenProtection',
            '--disable-gpu',
            '--disable-gpu-compositing',
            '--disable-software-rasterizer',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--allow-insecure-localhost'
        ]
        if webview_settings.get('ALLOW_FILE_URLS'):
            extra_args.append('--allow-file-access-from-files')
        if webview_settings.get('REMOTE_DEBUGGING_PORT') is not None:
            extra_args.append(f'--remote-debugging-port={webview_settings["REMOTE_DEBUGGING_PORT"]}')

        props.AdditionalBrowserArguments = ' '.join(extra_args)
        self.webview.CreationProperties = props

        self.form = form
        form.Controls.Add(self.webview)

        self.js_results = {}
        self.js_result_semaphore = Semaphore(0)
        self.webview.Dock = WinForms.DockStyle.Fill
        self.webview.BringToFront()
        self.webview.CoreWebView2InitializationCompleted += self.on_webview_ready
        self.webview.NavigationStarting += self.on_navigation_start
        self.webview.NavigationCompleted += self.on_navigation_completed
        self.webview.WebMessageReceived += self.on_script_notify
        self.syncContextTaskScheduler = TaskScheduler.FromCurrentSynchronizationContext()
        self.webview.DefaultBackgroundColor = Color.FromArgb(
            255,
            int(window.background_color.lstrip('#')[0:2], 16),
            int(window.background_color.lstrip('#')[2:4], 16),
            int(window.background_color.lstrip('#')[4:6], 16),
        )

        if window.transparent:
            self.webview.DefaultBackgroundColor = Color.Transparent

        self.url = None
        self.ishtml = False
        self.html = DEFAULT_HTML

        self.webview.EnsureCoreWebView2Async(None)

    ec.EdgeChrome.__init__ = patched_edge_init
    logging.info("Successfully installed EdgeChrome patch for Administrator black screen prevention.")
except Exception as e:
    logging.warning(f"Could not apply EdgeChrome patch: {e}")

# Global Window Handle
app_window = None
tray_icon = None
single_instance_mutex = None

def acquire_single_instance_mutex(is_elevating=False):
    """
    Creates a named Windows Global Mutex to strictly prevent duplicate launches across all privilege levels.
    If is_elevating=True, terminates any existing instances and waits to acquire the mutex.
    If another instance (either Admin or User) is already active, restores and focuses the existing window, then returns None.
    """
    MUTEX_NAME = "Global\\AntigravityNetworkSentinel_SingleInstance_Mutex"
    ERROR_ALREADY_EXISTS = 183
    ERROR_ACCESS_DENIED = 5

    if is_elevating:
        kill_previous_instances()
        # Retry for up to 3 seconds for old instance to fully exit and release mutex/port
        for _ in range(15):
            handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
            last_error = ctypes.windll.kernel32.GetLastError()
            if last_error not in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
                return handle
            time.sleep(0.2)
        # Force return handle since we are elevated
        return ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)

    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()

    # If mutex exists or access denied (meaning higher privilege Admin instance is already holding it)
    if last_error in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
        try:
            # Find existing window by title and bring to front
            hwnd = ctypes.windll.user32.FindWindowW(None, "Process Network Bandwidth Controller")
            if hwnd:
                SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            logging.error(f"Error focusing existing window: {e}")
        return None
    return handle


def kill_previous_instances():
    """
    Ensures single instance execution by terminating older instances of the app
    when elevating or relaunching.
    """
    import psutil
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            p_name = (proc.info['name'] or '').lower()
            p_cmd = ' '.join(proc.info['cmdline'] or []).lower()

            is_target = False
            if getattr(sys, 'frozen', False):
                if 'networksentinelapp' in p_name:
                    is_target = True
            else:
                if 'python' in p_name and 'main_desktop.py' in p_cmd:
                    is_target = True

            if is_target:
                logging.info(f"Terminating previous instance PID {proc.info['pid']}...")
                proc.terminate()
                try:
                    proc.wait(timeout=1.5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass

def run_server():
    try:
        import uvicorn
        from server import app
        # If port 8000 is briefly in TIME_WAIT from the previous instance, retry for a moment
        for attempt in range(15):
            try:
                config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
                server = uvicorn.Server(config)
                server.run()
                break
            except Exception as e:
                logging.warning(f"Uvicorn bind attempt {attempt+1} failed: {e}. Retrying in 0.3s...")
                time.sleep(0.3)
    except Exception as e:
        logging.error(f"Error running uvicorn server: {e}", exc_info=True)

def wait_for_server_ready(port=8000, timeout=10.0):
    """Waits until FastAPI backend is responding with 200 OK before creating WebView window."""
    import urllib.request
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/system-info", timeout=1.0) as resp:
                if resp.status == 200:
                    logging.info("FastAPI backend is ready and responding!")
                    return True
        except Exception:
            time.sleep(0.2)
    logging.warning("Timed out waiting for FastAPI backend to respond.")
    return False

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
    global app_window, single_instance_mutex

    is_elevated_arg = "--elevated" in sys.argv
    admin_active = False
    try:
        admin_active = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        pass

    # 1. Single Instance Check: if elevating or already admin, take over from previous instance
    is_elevating = is_elevated_arg or admin_active
    single_instance_mutex = acquire_single_instance_mutex(is_elevating=is_elevating)
    if not single_instance_mutex:
        logging.info("Another instance is already running. Focused existing window and exiting.")
        sys.exit(0)

    logging.info(f"App running mode: {'ADMIN' if admin_active else 'USER (Non-Admin)'}")

    logging.info("Starting background FastAPI server thread...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    logging.info("Starting background System Tray thread...")
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    logging.info("Waiting for FastAPI backend to be fully initialized...")
    wait_for_server_ready(port=8000, timeout=10.0)

    logging.info("Creating PyWebView desktop window...")
    app_window = webview.create_window(
        title="Process Network Bandwidth Controller",
        url=f"http://127.0.0.1:8000?v={int(time.time())}",
        width=1340,
        height=880,
        min_size=(1024, 700),
        resizable=True,
        text_select=True
    )

    app_window.events.closing += on_closing

    logging.info("Starting PyWebView event loop...")
    webview.start(private_mode=False, storage_path=WEBVIEW2_CACHE_DIR)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

