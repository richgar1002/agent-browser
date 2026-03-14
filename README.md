# 🤖 Agent Browser

AI-first headless browser with session persistence, network interception, and REST API.

## Features

### Core
- **Headless mode** — Fast, no UI overhead
- **API-first** — Control via REST API
- **Persistent sessions** — Stay logged in across restarts
- **Screenshots** — Visual confirmation

### Automation
- **Click, fill, type** — All standard interactions
- **JavaScript injection** — Run custom scripts
- **Element waiting** — Wait for elements to appear

### Network
- **Request/response logging** — See all network traffic
- **Request blocking** — Block ads, trackers
- **HAR export** — Save network logs

### Security
- **Cookie vault** — Secure session storage
- **Proxy support** — Route through proxies
- **Configurable user agent**

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run API
python api.py
```

## Example Usage

```python
from browser import create_browser

async def main():
    async with create_browser("my_session") as browser:
        # Navigate
        await browser.go_to("https://example.com")
        
        # Fill form
        await browser.fill("#username", "myuser")
        await browser.fill("#password", "mypass")
        await browser.click(".login-btn")
        
        # Wait for dashboard
        await browser.wait_for_selector(".dashboard")
        
        # Screenshot
        await browser.screenshot("dashboard.png")
        
        # Get data
        prices = await browser.get_all_text(".price")

asyncio.run(main())
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/go_to` | Navigate to URL |
| POST | `/click` | Click element |
| POST | `/fill` | Fill input |
| POST | `/screenshot` | Take screenshot |
| GET | `/network` | Get request log |
| POST | `/session/save` | Save session |
| GET | `/health` | Health check |

## Configuration

Set environment variables:
```env
HEADLESS=true
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080
DEFAULT_TIMEOUT=30000
PROXY_SERVER=http://proxy:8080
```

## Architecture

```
┌─────────────┐
│  REST API   │ (FastAPI)
└──────┬──────┘
       │
┌──────▼──────┐
│  Browser    │ (Playwright)
│  - Page     │
│  - Context  │
└──────┬──────┘
       │
┌──────▼──────┐
│  Storage    │
│  - Sessions │
│  - Cookies  │
│  - Screens  │
└─────────────┘
```
