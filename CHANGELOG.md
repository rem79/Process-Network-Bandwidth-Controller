# Changelog

All notable changes to the Process Network Bandwidth Controller project will be documented in this file.

## [2.0.0] - 2026-08-25

### Added
- **SQLite Traffic Analytics Engine (`history_db.py`)**: Persistent high-frequency sampling and daily/hourly data usage aggregations in `%APPDATA%/AntigravityNetworkSentinel/traffic_history.db`.
- **Socket Inspector Modal**: Real-time per-process socket inspection showing protocol (TCP/UDP), local/remote IP endpoints, and socket status.
- **QoS Priority Tagging**: High (DSCP 46), Normal, and Low (DSCP 10) QoS bandwidth policy levels.
- **PowerShell Parameter Sanitization**: Alphanumeric policy name sanitization and exe string filtering in `qos_manager.py`.
- **Navigation Tabs & Category Filtering**: Three distinct views (Live Sentinel, Traffic Analytics, Active QoS Policies) and dynamic category chips (All, Browsers, High Usage, Throttled).
- **Automated Test Suite**: 13 unit/integration tests covering SQLite persistence, QoS sanitization, and FastAPI REST endpoints in `tests/`.
- **PyInstaller Build Improvements**: Added hidden imports for `history_db` and `sqlite3` in `build_exe.py`.
- **Documentation**: Updated `README.md` and REST API specification.
