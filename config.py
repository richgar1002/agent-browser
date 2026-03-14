"""
Agent Browser - Core Configuration
"""
import os
from pathlib import Path

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
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
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
INTERCEPT_NETWORK = os.getenv("INTERCEPT_NETWORK", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_REQUESTS = os.getenv("LOG_REQUESTS", "true").lower() == "true"
LOG_RESPONSES = os.getenv("LOG_RESPONSES", "false").lower() == "true"

# Session persistence
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "168"))  # 7 days

# JavaScript injection
ALLOW_JS_INJECTION = os.getenv("ALLOW_JS_INJECTION", "true").lower() == "true"
