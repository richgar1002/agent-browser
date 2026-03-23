"""
Agent Browser - Core Configuration
"""
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    """Parse boolean env vars consistently."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    """Parse comma-separated env vars into list."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
COOKIES_DIR = DATA_DIR / "cookies"
LOGS_DIR = DATA_DIR / "logs"

# Create directories
for d in [DATA_DIR, SESSIONS_DIR, SCREENSHOTS_DIR, COOKIES_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Browser settings
HEADLESS = _env_bool("HEADLESS", True)
VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1920"))
VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "1080"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

# Timeout settings
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30000"))  # ms
NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", "60000"))

# Proxy settings (optional)
PROXY_SERVER = os.getenv("PROXY_SERVER", None)
PROXY_USERNAME = os.getenv("PROXY_USERNAME", None)
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", None)

# Screenshot settings
SCREENSHOT_FORMAT = os.getenv("SCREENSHOT_FORMAT", "png")  # png or jpeg
SCREENSHOT_QUALITY = int(os.getenv("SCREENSHOT_QUALITY", "80"))  # for jpeg

# Network interception
INTERCEPT_NETWORK = _env_bool("INTERCEPT_NETWORK", False)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_REQUESTS = _env_bool("LOG_REQUESTS", True)
LOG_RESPONSES = _env_bool("LOG_RESPONSES", False)

# Session persistence
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "168"))  # 7 days

# JavaScript injection
ALLOW_JS_INJECTION = _env_bool("ALLOW_JS_INJECTION", True)

# API / security defaults
CORS_ALLOW_ORIGINS = _env_list(
    "CORS_ALLOW_ORIGINS",
    "http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ALLOW_CREDENTIALS = _env_bool("CORS_ALLOW_CREDENTIALS", False)
