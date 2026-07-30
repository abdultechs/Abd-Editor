"""
App-wide constants for Abd Editor V1.0.
All magic values live here — never hardcoded elsewhere.
"""

import sys
import os

APP_NAME = "Abd Editor V1.0"
APP_VERSION = "1.0.0"
APP_ORG = "AbdEditor"

# ── Paths ────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    # Running inside compiled PyInstaller executable
    BASE_DIR = os.path.dirname(sys.executable)
    DATA_DIR = BASE_DIR
    ROOT_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = ROOT_DIR

SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
SETTINGS_DIR = os.path.join(DATA_DIR, "settings")
DB_PATH = os.path.join(DATA_DIR, "abd_editor.db")
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources")
STYLES_DIR = os.path.join(RESOURCES_DIR, "styles")

# Ensure all runtime directories exist
for _d in [DATA_DIR, SCRIPTS_DIR, LOGS_DIR, TEMP_DIR, EXPORTS_DIR, SETTINGS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ── Video ────────────────────────────────────────────────────────────────────
ACCEPTED_VIDEO_EXTENSIONS: set[str] = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

# ── Queue ────────────────────────────────────────────────────────────────────
DEFAULT_WORKER_COUNT = 1
MAX_WORKER_COUNT = 8

# ── Script JSON ──────────────────────────────────────────────────────────────
SCRIPT_VERSION = 1

# ── DB ───────────────────────────────────────────────────────────────────────
DB_SCHEMA_VERSION = 1

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE_NAME = "abd_editor.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# ── UI ───────────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 210
BOTTOM_PANEL_HEIGHT = 180
WINDOW_MIN_WIDTH = 920
WINDOW_MIN_HEIGHT = 640

# Status display colours (hex strings used in QSS and painter)
STATUS_COLORS = {
    "waiting":    "#F59E0B",
    "processing": "#3B82F6",
    "completed":  "#10B981",
    "failed":     "#EF4444",
    "cancelled":  "#6B7280",
}
