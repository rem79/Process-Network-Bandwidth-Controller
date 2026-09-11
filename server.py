import asyncio
import time
import os
import subprocess
import ctypes
import logging
import sys
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import psutil

from qos_manager import qos_manager
from history_db import history_db
import autostart_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="Antigravity Network Sentinel", version="2.0.0")

# Serve static frontend files (support PyInstaller bundle)
base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(base_dir, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Helper for formatted bytes (supports up to TB/s, GB/s, MB/s)
def format_bytes(bytes_num: float) -> str:
    if bytes_num < 1024:
        return f"{bytes_num:.1f} B/s"
    elif bytes_num < 1024 * 1024:
        return f"{(bytes_num / 1024):.1f} KB/s"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{(bytes_num / (1024 * 1024)):.2f} MB/s"
    elif bytes_num < 1024 * 1024 * 1024 * 1024:
        return f"{(bytes_num / (1024 * 1024 * 1024)):.2f} GB/s"
    else:
        return f"{(bytes_num / (1024 * 1024 * 1024 * 1024)):.2f} TB/s"

def format_total_bytes(bytes_num: float) -> str:
    if bytes_num < 1024:
        return f"{bytes_num:.0f} B"
    elif bytes_num < 1024 * 1024:
        return f"{(bytes_num / 1024):.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{(bytes_num / (1024 * 1024)):.1f} MB"
    elif bytes_num < 1024 * 1024 * 1024 * 1024:
        return f"{(bytes_num / (1024 * 1024 * 1024)):.2f} GB"
    else:
        return f"{(bytes_num / (1024 * 1024 * 1024 * 1024)):.2f} TB"

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

SYSTEM_UI_EXCLUDED_NAMES = {
    'msedgewebview2.exe', 'searchhost.exe', 'shellexperiencehost.exe',
    'dwm.exe', 'explorer.exe', 'textinputhost.exe', 'runtimebroker.exe',
    'startmenuexperiencehost.exe', 'system', 'registry', 'taskmgr.exe'
}

VM_EMULATOR_NAMES = {
    'ld9boxheadless.exe', 'ldboxheadless.exe', 'dnplayer.exe',
    'hd-player.exe', 'bluestacks.exe', 'nox.exe', 'noxvmhandle.exe',
    'virtualboxvm.exe', 'vboxheadless.exe', 'vmware-vmx.exe',
    'vmware.exe', 'qemu-system-x86_64.exe', 'vmmem', 'wsl.exe',
    'mumuplayer.exe', 'nemuplayer.exe', 'memu.exe', 'memuheadless.exe'
}

class ProcessTracker:
    def __init__(self):
        self.prev_global_io = psutil.net_io_counters()
        self.prev_proc_io: Dict[int, tuple[float, float, float, float]] = {} # pid -> (read_bytes, write_bytes, other_bytes, timestamp)
        self.prev_time = time.time()
        self.batch_counter = 0

    def get_snapshot(self) -> Dict[str, Any]:
        curr_time = time.time()
        dt = max(curr_time - self.prev_time, 0.001)
        self.prev_time = curr_time

        # 1. Global network interface throughput
        curr_global_io = psutil.net_io_counters()
        up_bytes_sec = max(0.0, (curr_global_io.bytes_sent - self.prev_global_io.bytes_sent) / dt)
        down_bytes_sec = max(0.0, (curr_global_io.bytes_recv - self.prev_global_io.bytes_recv) / dt)
        self.prev_global_io = curr_global_io

        global_stats = {
            "upload_speed": up_bytes_sec,
            "download_speed": down_bytes_sec,
            "upload_formatted": format_bytes(up_bytes_sec),
            "download_formatted": format_bytes(down_bytes_sec),
            "total_sent": curr_global_io.bytes_sent,
            "total_recv": curr_global_io.bytes_recv,
        }

        # 2. Get active network connections grouped by PID
        pid_conn_info: Dict[int, Dict[str, Any]] = {}
        unowned_remote_count = 0
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                # Active remote connection criteria:
                # 1. Non-loopback remote address
                # 2. For TCP: status is ESTABLISHED, SYN_SENT, or SYN_RECV (NOT TIME_WAIT, CLOSE_WAIT, LISTEN)
                # 3. For UDP: has remote address
                is_active_remote = False
                remote_ip = None
                if conn.raddr:
                    rip = getattr(conn.raddr, 'ip', None)
                    if rip and rip not in ('127.0.0.1', '::1', '0.0.0.0', '::') and not rip.startswith('127.'):
                        status = getattr(conn, 'status', None)
                        if status:
                            if status in ('ESTABLISHED', 'SYN_SENT', 'SYN_RECV'):
                                is_active_remote = True
                                remote_ip = rip
                        else:
                            is_active_remote = True
                            remote_ip = rip

                if conn.pid and conn.pid > 0:
                    if conn.pid not in pid_conn_info:
                        pid_conn_info[conn.pid] = {
                            "count": 0,
                            "has_remote": False,
                            "remote_count": 0,
                            "remote_ips": {}
                        }
                    pid_conn_info[conn.pid]["count"] += 1
                    if is_active_remote:
                        pid_conn_info[conn.pid]["has_remote"] = True
                        pid_conn_info[conn.pid]["remote_count"] += 1
                        if remote_ip:
                            ip_map = pid_conn_info[conn.pid]["remote_ips"]
                            ip_map[remote_ip] = ip_map.get(remote_ip, 0) + 1
                else:
                    if is_active_remote:
                        unowned_remote_count += 1
        except Exception as e:
            logging.debug(f"Error fetching net connections: {e}")

        # 3. Process IO collection & preliminary candidate evaluation
        raw_candidates: List[Dict[str, Any]] = []
        active_limits = qos_manager.get_all_limits()

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info']):
            try:
                pid = proc.info['pid']
                if pid <= 0:
                    continue

                name = proc.info['name'] or f"PID {pid}"
                exe = proc.info['exe'] or ""
                conn_info = pid_conn_info.get(pid)
                conn_count = conn_info["count"] if conn_info else 0
                has_remote = conn_info["has_remote"] if conn_info else False
                remote_count = conn_info["remote_count"] if conn_info else 0
                remote_ips = conn_info["remote_ips"] if conn_info else {}
                max_same_host_conns = max(remote_ips.values()) if remote_ips else (1 if has_remote else 0)
                is_limited = (name.lower() in active_limits or name in active_limits)
                is_excluded_ui = name.lower() in SYSTEM_UI_EXCLUDED_NAMES
                is_vm_emulator = name.lower() in VM_EMULATOR_NAMES

                # Get process IO counters
                io = None
                try:
                    io = proc.io_counters()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                read_bytes = 0
                write_bytes = 0
                other_bytes = 0
                if io:
                    rb = getattr(io, 'read_bytes', 0)
                    wb = getattr(io, 'write_bytes', 0)
                    ob = getattr(io, 'other_bytes', 0)
                    read_bytes = rb if isinstance(rb, (int, float)) else 0
                    write_bytes = wb if isinstance(wb, (int, float)) else 0
                    other_bytes = ob if isinstance(ob, (int, float)) else 0

                raw_r_rate = 0.0
                raw_w_rate = 0.0
                raw_o_rate = 0.0
                proc_dt = dt

                if pid in self.prev_proc_io:
                    prev_entry = self.prev_proc_io[pid]
                    if len(prev_entry) == 4:
                        prev_r, prev_w, prev_o, prev_t = prev_entry
                    else:
                        prev_r, prev_w, prev_t = prev_entry
                        prev_o = 0
                    proc_dt = max(curr_time - prev_t, 0.001)
                    raw_r_rate = max(0.0, (read_bytes - prev_r) / proc_dt)
                    raw_w_rate = max(0.0, (write_bytes - prev_w) / proc_dt)
                    raw_o_rate = max(0.0, (other_bytes - prev_o) / proc_dt)

                self.prev_proc_io[pid] = (read_bytes, write_bytes, other_bytes, curr_time)

                # Candidate attribution logic
                cand_down = 0.0
                cand_up = 0.0

                # Emulators and VMs continuously write guest OS memory, dalvik/art cache, and logs
                # to host virtual disk image files (e.g. data.vmdk, .vdi).
                # Their disk write_bytes and read_bytes MUST NOT be falsely counted as internet download or upload!
                eff_w_rate = 0.0 if is_vm_emulator else raw_w_rate
                eff_r_rate = 0.0 if is_vm_emulator else raw_r_rate

                # Determine if this process is eligible for network traffic attribution
                is_candidate = False
                if is_limited:
                    is_candidate = True
                elif has_remote:
                    # An emulator with only background keep-alives (max_same_host_conns < 4) is NOT
                    # an active bulk downloader unless it has real socket IO (raw_o_rate)
                    if is_vm_emulator and max_same_host_conns < 4 and raw_o_rate < 50 * 1024:
                        is_candidate = False
                    else:
                        is_candidate = True
                elif conn_count == 0 and unowned_remote_count > 0 and not is_excluded_ui and not is_vm_emulator and (down_bytes_sec > 1024 or up_bytes_sec > 1024):
                    # In Windows User Mode, elevated processes have their socket PIDs masked (conn.pid is None).
                    # If there are active unowned remote connections and process I/O activity correlates with network,
                    # qualify as an elevated candidate.
                    max_io = max(eff_r_rate, eff_w_rate, raw_o_rate)
                    if down_bytes_sec > up_bytes_sec * 1.5:
                        if max_io > 50 * 1024 and max_io <= down_bytes_sec * 2.5:
                            is_candidate = True
                    elif up_bytes_sec > down_bytes_sec * 1.5:
                        if max_io > 50 * 1024 and max_io <= up_bytes_sec * 2.5:
                            is_candidate = True
                    else:
                        total_net = down_bytes_sec + up_bytes_sec
                        if max_io > 50 * 1024 and max_io <= total_net * 2.5:
                            is_candidate = True

                if is_candidate:
                    if down_bytes_sec > up_bytes_sec * 1.5:
                        # Dominant system download (e.g. game patcher, browser file download, streaming)
                        # Downloaded chunks written to disk (write_bytes), socket read (read_bytes),
                        # or Winsock socket AFD/IOCTLs (other_bytes)
                        cand_down = max(eff_r_rate, eff_w_rate, raw_o_rate)
                        cand_up = min(min(eff_r_rate, eff_w_rate), up_bytes_sec)
                    elif up_bytes_sec > down_bytes_sec * 1.5:
                        # Dominant system upload (e.g. cloud backup, file upload)
                        # File read from disk (read_bytes) or socket send (write_bytes/other_bytes)
                        cand_up = max(eff_r_rate, eff_w_rate, raw_o_rate)
                        cand_down = min(min(eff_r_rate, eff_w_rate), down_bytes_sec)
                    else:
                        # Mixed / balanced traffic
                        best_rate = max(eff_r_rate, eff_w_rate, raw_o_rate)
                        if down_bytes_sec >= up_bytes_sec:
                            cand_down = best_rate
                            cand_up = min(eff_r_rate, up_bytes_sec)
                        else:
                            cand_up = best_rate
                            cand_down = min(eff_w_rate, down_bytes_sec)

                    # If conn_count was 0 due to User Mode UAC masking, give at least 1 socket indication
                    if conn_count == 0 and not is_excluded_ui and not is_vm_emulator and (cand_down > 50 * 1024 or cand_up > 50 * 1024):
                        conn_count = max(1, min(unowned_remote_count, 8))
                        remote_count = conn_count
                        has_remote = True
                        max_same_host_conns = remote_count

                mem_mb = (proc.info['memory_info'].rss / (1024 * 1024)) if proc.info['memory_info'] else 0.0
                proc_limit = active_limits.get(name) or active_limits.get(name.lower())

                raw_candidates.append({
                    "pid": pid,
                    "name": name,
                    "exe": exe,
                    "conn_count": conn_count,
                    "has_remote": has_remote,
                    "remote_count": remote_count,
                    "max_same_host_conns": max_same_host_conns,
                    "cand_down": cand_down,
                    "cand_up": cand_up,
                    "proc_dt": proc_dt,
                    "cpu_percent": proc.info['cpu_percent'] or 0.0,
                    "memory_mb": round(mem_mb, 1),
                    "proc_limit": proc_limit
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # 4. Global calibration and unallocated bandwidth attribution
        total_cand_down = sum(c["cand_down"] for c in raw_candidates)
        total_cand_up = sum(c["cand_up"] for c in raw_candidates)

        # 4a. If global download exceeds sum of candidate IO rates
        # (e.g. game patcher, curl, or memory-buffered Winsock stream without synchronous disk writes),
        # distribute unallocated download throughput to processes with active remote connections.
        if down_bytes_sec > total_cand_down and down_bytes_sec > 50 * 1024:
            unallocated_down = down_bytes_sec - total_cand_down
            # Filter candidate downloaders:
            # 1. Must have remote connections and not be a system UI renderer
            # 2. Exclude VM emulators unless they have parallel streams to the same host (>= 4 conns)
            net_downloaders = [
                c for c in raw_candidates
                if c["has_remote"]
                and c["name"].lower() not in SYSTEM_UI_EXCLUDED_NAMES
                and (c["name"].lower() not in VM_EMULATOR_NAMES or c.get("max_same_host_conns", 0) >= 4)
            ]
            # Fallback if only emulators are active on the system
            if not net_downloaders:
                net_downloaders = [
                    c for c in raw_candidates
                    if c["has_remote"] and c["name"].lower() not in SYSTEM_UI_EXCLUDED_NAMES
                ]
            if net_downloaders:
                # Parallel stream concentration factor:
                # Sockets to the SAME remote host represent concurrent parallel download chunks.
                # Scatter sockets across different hosts represent background keep-alive/push sockets.
                # Weight by (max_same_host_conns ** 2) * max(1, remote_count)
                weights = [
                    (max(1, c.get("max_same_host_conns", 1)) ** 2) * max(1, c.get("remote_count", 1))
                    for c in net_downloaders
                ]
                sum_weights = sum(weights)
                if sum_weights > 0:
                    for c, w in zip(net_downloaders, weights):
                        c["cand_down"] += unallocated_down * (w / sum_weights)
            total_cand_down = sum(c["cand_down"] for c in raw_candidates)

        # 4b. Symmetrically for dominant upload
        if up_bytes_sec > total_cand_up and up_bytes_sec > 50 * 1024:
            unallocated_up = up_bytes_sec - total_cand_up
            net_uploaders = [
                c for c in raw_candidates
                if c["has_remote"]
                and c["name"].lower() not in SYSTEM_UI_EXCLUDED_NAMES
                and (c["name"].lower() not in VM_EMULATOR_NAMES or c.get("max_same_host_conns", 0) >= 4)
            ]
            if not net_uploaders:
                net_uploaders = [
                    c for c in raw_candidates
                    if c["has_remote"] and c["name"].lower() not in SYSTEM_UI_EXCLUDED_NAMES
                ]
            if net_uploaders:
                weights = [
                    (max(1, c.get("max_same_host_conns", 1)) ** 2) * max(1, c.get("remote_count", 1))
                    for c in net_uploaders
                ]
                sum_weights = sum(weights)
                if sum_weights > 0:
                    for c, w in zip(net_uploaders, weights):
                        c["cand_up"] += unallocated_up * (w / sum_weights)
            total_cand_up = sum(c["cand_up"] for c in raw_candidates)

        scale_down = 1.0
        if total_cand_down > down_bytes_sec * 1.05 and down_bytes_sec > 1024:
            scale_down = down_bytes_sec / total_cand_down

        scale_up = 1.0
        if total_cand_up > up_bytes_sec * 1.05 and up_bytes_sec > 1024:
            scale_up = up_bytes_sec / total_cand_up

        proc_list: List[Dict[str, Any]] = []
        db_samples: List[Dict[str, Any]] = []

        for c in raw_candidates:
            p_down_speed = c["cand_down"] * scale_down
            p_up_speed = c["cand_up"] * scale_up

            # Ensure single process cannot exceed global adapter rate
            if down_bytes_sec > 0:
                p_down_speed = min(p_down_speed, down_bytes_sec * 1.15)
            else:
                p_down_speed = 0.0

            if up_bytes_sec > 0:
                p_up_speed = min(p_up_speed, up_bytes_sec * 1.15)
            else:
                p_up_speed = 0.0

            delta_down = p_down_speed * c["proc_dt"]
            delta_up = p_up_speed * c["proc_dt"]

            # Collect for DB history if active
            if delta_up > 0 or delta_down > 0:
                db_samples.append({
                    "pid": c["pid"],
                    "name": c["name"],
                    "exe": c["exe"],
                    "up_bytes": delta_up,
                    "down_bytes": delta_down,
                    "timestamp": curr_time
                })

            if c["conn_count"] > 0 or p_up_speed > 100 or p_down_speed > 100 or c["proc_limit"]:
                proc_list.append({
                    "pid": c["pid"],
                    "name": c["name"],
                    "exe": c["exe"],
                    "up_speed": p_up_speed,
                    "down_speed": p_down_speed,
                    "up_formatted": format_bytes(p_up_speed),
                    "down_formatted": format_bytes(p_down_speed),
                    "connections": c["conn_count"],
                    "cpu_percent": c["cpu_percent"],
                    "memory_mb": c["memory_mb"],
                    "limit_kbps": c["proc_limit"]["kbps"] if c["proc_limit"] else None,
                    "priority": c["proc_limit"].get("priority", "normal") if c["proc_limit"] else None
                })

        # Record to SQLite DB
        if db_samples:
            history_db.record_traffic_batch(db_samples)

        # Sort by total active throughput descending
        proc_list.sort(key=lambda x: (x['down_speed'] + x['up_speed']), reverse=True)

        # Cleanup terminated PIDs from tracking dictionary (only remove truly exited processes)
        observed_pids = set(c['pid'] for c in raw_candidates)
        self.prev_proc_io = {p: data for p, data in self.prev_proc_io.items() if p in observed_pids}

        # Periodic cleanup of old sample entries every 300 cycles (~5 minutes)
        self.batch_counter += 1
        if self.batch_counter % 300 == 0:
            history_db.cleanup_old_samples(retention_days=14)

        return {
            "timestamp": curr_time,
            "is_admin": is_admin(),
            "global": global_stats,
            "processes": proc_list,
            "active_limits": active_limits
        }

tracker = ProcessTracker()

# Connected WebSocket clients
connected_clients: List[WebSocket] = []

@app.websocket("/ws/stats")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(3600)
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def broadcast_loop():
    while True:
        try:
            snapshot = tracker.get_snapshot()
            if connected_clients:
                dead_clients = []
                for client in connected_clients:
                    try:
                        await client.send_json(snapshot)
                    except Exception:
                        dead_clients.append(client)
                for client in dead_clients:
                    if client in connected_clients:
                        connected_clients.remove(client)
        except Exception as e:
            logging.error(f"Error in broadcast loop: {e}")
        await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_loop())

class LimitRequest(BaseModel):
    target: str          # Process name e.g. "chrome.exe" or "global"
    app_exe: str = ""    # Optional full app exe path or process name
    limit_kbps: int      # Speed limit in KB/s (0 to remove)
    priority: str = "normal" # Priority: "high", "normal", "low"

@app.post("/api/limit")
def set_limit(req: LimitRequest):
    app_exe = req.app_exe or req.target
    if req.target.lower() == "global":
        app_exe = "*"
    success, msg = qos_manager.set_limit(req.target, app_exe, req.limit_kbps, priority=req.priority)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok", "message": msg}

@app.delete("/api/limit/{target}")
def remove_limit(target: str):
    success, msg = qos_manager.remove_limit(target)
    return {"status": "ok", "message": msg}

@app.post("/api/limits/clear")
def clear_all_limits():
    success, msg = qos_manager.clear_all_limits()
    return {"status": "ok", "message": msg}

@app.get("/api/limits")
def get_limits():
    return qos_manager.get_all_limits()

@app.get("/api/system-info")
def system_info():
    return {
        "is_admin": is_admin(),
        "autostart": autostart_manager.is_autostart_enabled(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "os": "Windows"
    }

@app.post("/api/system/elevate")
def request_elevation():
    """Triggers Windows UAC prompt to relaunch controller with Admin privileges."""
    if is_admin():
        return {"status": "ok", "message": "Already running with Administrator privileges"}
    try:
        if getattr(sys, 'frozen', False):
            executable = sys.executable
            params = "--elevated"
            work_dir = os.path.dirname(os.path.abspath(executable))
        else:
            executable = sys.executable
            desktop_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_desktop.py")
            params = f'"{desktop_main}" --elevated'
            work_dir = os.path.dirname(os.path.abspath(__file__))

        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, work_dir, 1)
        if ret > 32:
            # Terminate current non-admin instance quickly so the new elevated instance gets port 8000 and single-window ownership
            def delayed_exit():
                time.sleep(0.1)
                os._exit(0)
            
            import threading
            threading.Thread(target=delayed_exit, daemon=True).start()
            return {"status": "ok", "message": "Administrator elevation granted. Relaunching..."}
        else:
            return {"status": "error", "message": "UAC privilege elevation was cancelled by user"}
    except Exception as e:
        return {"status": "error", "message": f"Elevation error: {str(e)}"}

class AutostartRequest(BaseModel):
    enable: bool

@app.post("/api/autostart")
def toggle_autostart(req: AutostartRequest):
    success, msg = autostart_manager.set_autostart(req.enable)
    return {"status": "ok" if success else "error", "message": msg, "autostart": autostart_manager.is_autostart_enabled()}

@app.get("/api/autostart")
def get_autostart():
    return {"autostart": autostart_manager.is_autostart_enabled()}

# Analytics & History Endpoints
@app.get("/api/history/top")
def get_top_consumers(
    period: str = Query("today", description="Time window: today, 10m, 1h, 3h, 6h, 12h, 18h, 24h"),
    hours: Optional[float] = Query(None),
    limit: int = Query(500, ge=1, le=1000)
):
    today_only = False
    p_hours = 24.0

    if period == "today":
        today_only = True
    elif period == "10m":
        p_hours = 10.0 / 60.0
    elif period == "1h":
        p_hours = 1.0
    elif period == "3h":
        p_hours = 3.0
    elif period == "6h":
        p_hours = 6.0
    elif period == "12h":
        p_hours = 12.0
    elif period == "18h":
        p_hours = 18.0
    elif period == "24h":
        p_hours = 24.0
    elif hours is not None:
        p_hours = float(hours)

    items = history_db.get_top_consumers(period_hours=p_hours, limit=limit, today_only=today_only)
    for item in items:
        item["total_traffic_formatted"] = format_total_bytes(item["total_traffic_bytes"])
        item["total_up_formatted"] = format_total_bytes(item["total_up_bytes"])
        item["total_down_formatted"] = format_total_bytes(item["total_down_bytes"])
    return items

@app.get("/api/history/timeline")
def get_timeline(minutes: int = Query(60, ge=5, le=1440)):
    return history_db.get_timeline_stats(minutes=minutes)

@app.get("/api/history/daily")
def get_daily(days: int = Query(7, ge=1, le=90)):
    items = history_db.get_daily_history(days=days)
    for item in items:
        item["total_formatted"] = format_total_bytes(item["total_bytes"])
        item["up_formatted"] = format_total_bytes(item["total_up_bytes"])
        item["down_formatted"] = format_total_bytes(item["total_down_bytes"])
    return items

# Network Inspector & Diagnostics Endpoints (v3.0)
import network_inspector
import diagnostics

class KillSocketRequest(BaseModel):
    pid: int
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int

class NslookupRequest(BaseModel):
    domain: str
    custom_dns: Optional[str] = None

class TracerouteRequest(BaseModel):
    target: str

@app.get("/api/process/{pid}/connections")
def get_process_connections(pid: int):
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        conns = proc.connections(kind='inet')
        results = []
        for c in conns:
            l_ip = c.laddr.ip if c.laddr else "0.0.0.0"
            l_port = c.laddr.port if c.laddr else 0
            r_ip = c.raddr.ip if c.raddr else "N/A"
            r_port = c.raddr.port if c.raddr else 0

            # GeoIP & Reverse DNS
            geo = network_inspector.resolve_geoip_sync(r_ip)
            rdns = network_inspector.resolve_rdns_sync(r_ip) if r_ip != "N/A" else ""
            threat = network_inspector.inspect_threat(r_ip, r_port, proc_name)
            latency = network_inspector.measure_latency_ms_sync(r_ip, r_port) if r_ip != "N/A" else 1.0

            results.append({
                "fd": getattr(c, 'fd', -1),
                "family": str(c.family.name) if hasattr(c.family, 'name') else str(c.family),
                "type": "TCP" if c.type == 1 else "UDP",
                "local_ip": l_ip,
                "local_port": l_port,
                "remote_ip": r_ip,
                "remote_port": r_port,
                "local_address": f"{l_ip}:{l_port}",
                "remote_address": f"{r_ip}:{r_port}" if r_ip != "N/A" else "N/A",
                "rdns": rdns or (geo["org"] if geo["org"] != "Public Internet Server" else r_ip),
                "country": geo["country"],
                "flag": geo["flag"],
                "org": geo["org"],
                "lat": geo["lat"],
                "lon": geo["lon"],
                "latency_ms": latency,
                "threat": threat,
                "status": c.status if c.status else ("LISTENING" if c.type == 1 else "ACTIVE")
            })
        return {
            "pid": pid,
            "name": proc_name,
            "connections": results,
            "count": len(results)
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
        return {
            "pid": pid,
            "name": f"PID {pid}",
            "connections": [],
            "count": 0,
            "error": str(e)
        }

@app.post("/api/socket/kill")
def kill_socket_endpoint(req: KillSocketRequest):
    success = network_inspector.kill_socket_connection(
        req.pid, req.local_ip, req.local_port, req.remote_ip, req.remote_port
    )
    if success:
        return {"status": "ok", "message": f"Terminated TCP connection {req.remote_ip}:{req.remote_port}"}
    return {"status": "error", "message": f"Could not terminate connection to {req.remote_ip}:{req.remote_port}"}

@app.post("/api/diagnostics/nslookup")
def nslookup_endpoint(req: NslookupRequest):
    return diagnostics.run_nslookup(req.domain, req.custom_dns)

@app.post("/api/diagnostics/traceroute")
def traceroute_endpoint(req: TracerouteRequest):
    return diagnostics.run_visual_traceroute(req.target)

class PortTestRequest(BaseModel):
    host: str
    port: int

class PingSampleRequest(BaseModel):
    host: str

@app.get("/api/diagnostics/health")
def health_endpoint():
    return diagnostics.get_wifi_lan_health()

@app.post("/api/diagnostics/flush")
def flush_network_endpoint():
    """Flushes DNS Resolver cache, ARP table, and refreshes network stack"""
    return diagnostics.flush_network_stack()

@app.post("/api/diagnostics/port-test")
def port_test_endpoint(req: PortTestRequest):
    """Tests TCP 3-Way Handshake reachability to target host and port"""
    return diagnostics.test_tcp_port(req.host, req.port)

@app.post("/api/diagnostics/ping-sample")
def ping_sample_endpoint(req: PingSampleRequest):
    """Fast single-probe latency measurement for continuous jitter monitoring"""
    return diagnostics.ping_target_latency(req.host)

@app.get("/api/diagnostics/ipconfig")
def ipconfig_endpoint():
    """Executes ipconfig /all and returns raw output and parsed network adapter telemetry"""
    return diagnostics.get_ipconfig_all()

class ExportReportRequest(BaseModel):
    html_content: str
    filename: Optional[str] = None

class OpenFolderRequest(BaseModel):
    file_path: str

@app.post("/api/diagnostics/export-report")
def export_report_endpoint(req: ExportReportRequest):
    """Saves HTML diagnostic report to User's Desktop and opens it in default browser"""
    user_home = os.path.expanduser("~")
    # Check regular Desktop or OneDrive Desktop
    candidates = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "OneDrive", "Desktop"),
        os.path.join(user_home, "OneDrive - Personal", "Desktop"),
        os.path.join(user_home, "Downloads"),
        os.getcwd()
    ]
    desktop_dir = os.getcwd()
    for c in candidates:
        if os.path.exists(c):
            desktop_dir = c
            break

    file_name = req.filename or f"NetworkSentinel_Report_{time.strftime('%Y%m%d_%H%M%S')}.html"
    file_path = os.path.join(desktop_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.html_content)

    # Open file automatically in default browser
    try:
        if os.name == 'nt':
            os.startfile(file_path)
        else:
            webbrowser.open(f"file://{os.path.abspath(file_path)}")
    except Exception as e:
        logger.warning(f"Could not auto-launch browser for report: {e}")

    return {
        "status": "ok",
        "file_path": file_path,
        "filename": file_name,
        "desktop_dir": desktop_dir,
        "message": f"Diagnostic report saved successfully to {file_path}"
    }

@app.post("/api/diagnostics/open-folder")
def open_folder_endpoint(req: OpenFolderRequest):
    """Opens Windows Explorer and highlights target report file"""
    target = req.file_path.strip()
    if os.path.exists(target):
        if os.name == 'nt':
            subprocess.Popen(f'explorer /select,"{os.path.abspath(target)}"')
        else:
            subprocess.Popen(['xdg-open', os.path.dirname(target)])
        return {"status": "ok", "message": "Opened file in explorer."}
    return {"status": "error", "message": "File path does not exist."}


@app.get("/api/map/connections")
def global_map_connections():
    """Aggregates all active outbound connections across processes for Global Cyber Map"""
    active_nodes = []
    seen = set()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            conns = proc.connections(kind='inet')
            for c in conns:
                if c.raddr and not network_inspector.is_private_ip(c.raddr.ip):
                    r_ip = c.raddr.ip
                    if r_ip not in seen:
                        seen.add(r_ip)
                        geo = network_inspector.resolve_geoip_sync(r_ip)
                        rdns = network_inspector.resolve_rdns_sync(r_ip)
                        active_nodes.append({
                            "ip": r_ip,
                            "port": c.raddr.port,
                            "proc_name": proc.info['name'],
                            "rdns": rdns or geo["org"],
                            "country": geo["country"],
                            "flag": geo["flag"],
                            "org": geo["org"],
                            "lat": geo["lat"],
                            "lon": geo["lon"],
                            "latency_ms": network_inspector.measure_latency_ms_sync(r_ip, c.raddr.port)
                        })
                        if len(active_nodes) >= 30: # Capped for performance
                            break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return active_nodes

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
