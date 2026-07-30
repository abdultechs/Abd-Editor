"""
Enums used across the application.
"""

from enum import Enum


class JobStatus(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    DEBUG = "debug"


class AppView(str, Enum):
    DASHBOARD = "dashboard"
    SCRIPTS = "scripts"
    JOBS = "jobs"
    HISTORY = "history"
    SETTINGS = "settings"
    AI_FEATURES = "ai_features"
