import asyncio
import time
import os
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

class ProcessTracker:
    def __init__(self):
        self.prev_global_io = psutil.net_io_counters()
        self.prev_proc_io: Dict[int, tuple[float, float, float]] = {} # pid -> (read_bytes, write_bytes, timestamp)
        self.prev_time = time.time()
        self.batch_counter = 0

    def get_snapshot(self) -> Dict[str, Any]:
        curr_time = time.time()
        dt = max(curr_time - self.prev_time, 0.001)
        self.prev_time = curr_time

        # 1. Global IO calculation
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
        pid_connections: Dict[int, int] = {}
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                if conn.pid and conn.pid > 0:
                    pid_connections[conn.pid] = pid_connections.get(conn.pid, 0) + 1
        except Exception as e:
            logging.debug(f"Error fetching net connections: {e}")

        # 3. Process IO calculation & DB sampling
        proc_list: List[Dict[str, Any]] = []
        db_samples: List[Dict[str, Any]] = []
        active_limits = qos_manager.get_all_limits()

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info']):
            try:
                pid = proc.info['pid']
                if pid <= 0:
                    continue

                name = proc.info['name'] or f"PID {pid}"
                exe = proc.info['exe'] or ""
                conn_count = pid_connections.get(pid, 0)

                # Get process IO counters
                io = None
                try:
                    io = proc.io_counters()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                read_bytes = io.read_bytes if io else 0
                write_bytes = io.write_bytes if io else 0

                p_up_speed = 0.0
                p_down_speed = 0.0
                delta_down = 0.0
                delta_up = 0.0

                if pid in self.prev_proc_io:
                    prev_r, prev_w, prev_t = self.prev_proc_io[pid]
                    proc_dt = max(curr_time - prev_t, 0.001)
                    # read_bytes represents received traffic, write_bytes represents sent traffic
                    delta_down = max(0.0, read_bytes - prev_r)
                    delta_up = max(0.0, write_bytes - prev_w)
                    p_down_speed = delta_down / proc_dt
                    p_up_speed = delta_up / proc_dt

                self.prev_proc_io[pid] = (read_bytes, write_bytes, curr_time)

                # If process has network activity or connections, collect for DB and UI
                if delta_up > 0 or delta_down > 0:
                    db_samples.append({
                        "pid": pid,
                        "name": name,
                        "exe": exe,
                        "up_bytes": delta_up,
                        "down_bytes": delta_down,
                        "timestamp": curr_time
                    })

                if conn_count > 0 or p_up_speed > 100 or p_down_speed > 100 or name.lower() in active_limits:
                    mem_mb = (proc.info['memory_info'].rss / (1024 * 1024)) if proc.info['memory_info'] else 0.0
                    proc_limit = active_limits.get(name) or active_limits.get(name.lower())

                    proc_list.append({
                        "pid": pid,
                        "name": name,
                        "exe": exe,
                        "up_speed": p_up_speed,
                        "down_speed": p_down_speed,
                        "up_formatted": format_bytes(p_up_speed),
                        "down_formatted": format_bytes(p_down_speed),
                        "connections": conn_count,
                        "cpu_percent": proc.info['cpu_percent'] or 0.0,
                        "memory_mb": round(mem_mb, 1),
                        "limit_kbps": proc_limit["kbps"] if proc_limit else None,
                        "priority": proc_limit.get("priority", "normal") if proc_limit else None
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Record to SQLite DB
        if db_samples:
            history_db.record_traffic_batch(db_samples)

        # Sort by total active throughput descending
        proc_list.sort(key=lambda x: (x['down_speed'] + x['up_speed']), reverse=True)

        # Cleanup terminated PIDs from tracking dictionary
        active_pids = set(p['pid'] for p in proc_list)
        self.prev_proc_io = {p: data for p, data in self.prev_proc_io.items() if p in active_pids}

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
def get_top_consumers(hours: int = Query(24, ge=1, le=720), limit: int = Query(10, ge=1, le=100)):
    items = history_db.get_top_consumers(period_hours=hours, limit=limit)
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
    return diagnostics.run_nslookup(req.domain)

@app.post("/api/diagnostics/traceroute")
def traceroute_endpoint(req: TracerouteRequest):
    return diagnostics.run_visual_traceroute(req.target)

@app.get("/api/diagnostics/health")
def health_endpoint():
    return diagnostics.get_wifi_lan_health()

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
