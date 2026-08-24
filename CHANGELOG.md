# Changelog

All notable changes to the Process Network Bandwidth Controller project will be documented in this file.

## [2.3.0] - 2026-08-25

### Added
- **Interactive Bidirectional Table Header Sorting**: Added interactive click sorting with ascending (▲) and descending (▼) toggle icons to all column headers across both the **Live Process Sentinel Table** (`APPLICATION`, `PID`, `CONNECTIONS`, `DOWNLOAD SPEED`, `UPLOAD SPEED`, `CPU / RAM`, `LIMIT STATUS`) and the **Daily Analytics History Table** (`DATE`, `APPLICATION`, `UPLOAD`, `DOWNLOAD`, `TOTAL DATA`).
- **Non-blocking Neon Toast Notification System**: Replaced all blocking browser modal alerts with responsive cyber-neon toast notifications and full UI crash protection.
- **Active QoS Rule Adjustment**: Added an **`Adjust Limit`** action button to each configured policy card in the Active QoS Rules tab, allowing users to modify existing limits, presets, and priorities on the fly.
- **Micro-Bandwidth Presets**: Added 10 KB/s, 100 KB/s, and 500 KB/s ultra-low speed limit presets for extreme traffic throttling tests.

## [2.1.0] - 2026-08-25

### Fixed
- **Windows QoS Policy Throttling Match**: Fixed Windows `NetQosPolicy` `-AppPathNameMatchCondition` to pass pure executable filenames (e.g. `chrome.exe` instead of malformed absolute paths), ensuring Windows QoS engine correctly throttles Chrome/Netflix streaming traffic.

### Changed
- **Global Speed Limit Presets**: Updated quick preset buttons on the dashboard to **10 MB/s**, **100 MB/s**, **1 GB/s**, and **Off** for high-speed network environments.
- **Traffic Analytics QoS Creation**: Added direct QoS Limit creation buttons to both **Top Bandwidth Consumers (24h)** list items and **Daily Data Usage Summary** table rows.

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
