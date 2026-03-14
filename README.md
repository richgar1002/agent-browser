# 🤖 Agent Browser

AI-first headless browser with session persistence, network interception, and REST API.

## Phase 1 - MVP ✅

### What's Built

| Feature | Status |
|---------|--------|
| Headless browser (Playwright) | ✅ |
| Basic navigation | ✅ |
| Click/Fill interaction | ✅ |
| Screenshots | ✅ |
| Session persistence | ✅ |
| REST API | ✅ |
| CLI | ✅ |
| Error handling + retry | ✅ |
| Session pooling | ✅ |
| Network interception | ✅ |
| Ad/tracker blocking | ✅ |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run API
python api.py

# Or use CLI
python cli.py goto https://example.com
python cli.py screenshot --path screenshot.png
python cli.py session list
```

## CLI Commands

```bash
# Navigation
python cli.py goto https://tradingview.com
python cli.py screenshot --url https://example.com
python cli.py click .login-btn --url https://example.com
python cli.py fill #username myuser --url https://example.com

# JavaScript
python cli.py evaluate "document.title"

# Network
python cli.py network --url https://example.com

# Sessions
python cli.py session list
python cli.py session delete my_session
```

## Python SDK

```python
from browser import create_browser

async with create_browser("trading") as b:
    await b.go_to("https://tradingview.com")
    await b.wait_for_selector(".chart")
    await b.screenshot("chart.png")
    
    # Fill form
    await b.fill("#username", "user")
    await b.fill("#password", "pass")
    await b.click(".login-btn")
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Browser                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │    CLI     │   │ REST API   │   │ Python SDK  │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │              │
│  ┌──────▼─────────────────▼─────────────────▼──────┐       │
│  │           Enhanced Browser Engine               │       │
│  │  - Retry logic    - Error handling             │       │
│  │  - Session pool   - Network interception       │       │
│  └─────────────────────┬───────────────────────┘       │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────┐       │
│  │            Playwright (Chromium)            │       │
│  └──────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────┐         │
│  │                 Storage                      │         │
│  │  Sessions │ Cookies │ Screenshots │ Logs     │         │
│  └──────────────────────────────────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Session Management
- Persistent sessions (cookies, localStorage)
- Session pooling for fast context switching
- Auto-cleanup of idle sessions

### Error Handling
- Automatic retry with exponential backoff
- Structured error logging
- Recovery from common failures

### Network
- Request/response logging
- API call detection
- Ad/tracker blocking
- HAR export

### Automation
- Click, fill, type
- JavaScript injection
- Element waiting
- Form handling

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

```env
HEADLESS=true
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080
DEFAULT_TIMEOUT=30000
SESSION_EXPIRY_HOURS=168
```

## Requirements

- Python 3.10+
- Playwright
- Chromium browser

## Roadmap

### Phase 2 - Automation
- [ ] JavaScript injection wrapper
- [ ] Form builders
- [ ] Recording/playback

### Phase 3 - AI Integration
- [ ] Page summarization (LLM)
- [ ] Visual QA
- [ ] Smart selectors

### Phase 4 - Enterprise
- [ ] Multi-user support
- [ ] Team workspaces
- [ ] Cloud sync
