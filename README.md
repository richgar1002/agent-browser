# 🤖 Agent Browser

AI-first headless browser with session persistence, network interception, memory integration, and REST API.

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

## Phase 2 - Automation ✅

| Feature | Status |
|---------|--------|
| **Memory Integration** | ✅ |
| Form Builder | ✅ |
| Action Recorder | ✅ |
| Screenshot Analysis | ✅ |

## Phase 3 - Enterprise ✅

| Feature | Status |
|---------|--------|
| Session Pool Manager | ✅ |
| Multi-profile support | ✅ |
| Proxy rotation | ✅ |
| Network Interceptor (Advanced) | ✅ |
| Webhook System | ✅ |

---

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

## Memory Integration

```python
from memory_integration import create_browser_memory, PageSummary

# Create memory client
memory = create_browser_memory(user_id="richgar")

# Save page to memory
page = PageSummary(
    url="https://example.com",
    title="Example",
    content="Page content..."
)
memory.save_page(page)

# Search memory while browsing
results = memory.search_memory("trading")
```

## Form Builder

```python
from form_builder import create_form_builder

builder = create_form_builder("./data")

# Create a form
form = builder.create_form("Login Form", "https://example.com/login")

# Add fields
builder.add_field(form.id, "username", "#username")
builder.add_field(form.id, "password", "#password", field_type="password")
builder.set_submit_button(form.id, ".login-btn")

# Fill with data
fill_data = builder.fill_form_data(form.id, {"username": "user"})
```

## Action Recorder

```python
from action_recorder import create_action_recorder, ActionType

recorder = create_action_recorder("./data")

# Start recording
recorder.start_recording("Login Flow")

# Record actions
recorder.record_navigate("https://example.com/login")
recorder.record_type("#username", "user")
recorder.record_type("#password", "pass")
recorder.record_click(".login-btn")

# Stop and save
workflow = recorder.stop_recording()

# Replay
for action in workflow.actions:
    await browser.execute(action)
```

## Screenshot Analysis

```python
from screenshot_analyzer import create_screenshot_analyzer

analyzer = create_screenshot_analyzer()

# Analyze screenshot
result = analyzer.analyze("screenshot.png")

print(result.text)      # Extracted text
print(result.buttons)  # Found buttons
print(result.summary)   # AI summary

# Compare screenshots
diff = analyzer.compare_screenshots("before.png", "after.png")
```

## Webhooks

```python
from webhook_manager import create_webhook_manager, TriggerType

webhooks = create_webhook_manager("./data")

# Create webhook
webhooks.create_webhook(
    name="Price Alert",
    url="https://your-server.com/webhook",
    trigger_type=TriggerType.TEXT_MATCHES,
    trigger_value="Price:"
)

# Trigger on content change
webhooks.check_triggers(TriggerType.TEXT_MATCHES, "Price: $1000", context)
```

## Session Pool

```python
from session_pool_manager import create_session_pool

pool = create_session_pool(min_sessions=2, max_sessions=10)

# Create profile with proxy
profile = pool.create_profile("Trading", proxy="http://proxy:8080")

# Acquire session
session = pool.acquire_session(profile.id)

# Use browser...

# Release back to pool
pool.release_session(session.id)
```

## CLI Commands

```bash
# Navigation
python cli.py goto https://tradingview.com
python cli.py screenshot --url https://example.com
python cli.py click .login-btn --url https://example.com

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
```

---

## New Files

| File | Description |
|------|-------------|
| `memory_integration.py` | Browser ↔ Memory Bridge |
| `form_builder.py` | Visual form builder |
| `action_recorder.py` | Record & replay workflows |
| `screenshot_analyzer.py` | OCR & AI analysis |
| `webhook_manager.py` | Event webhooks |
| `session_pool_manager.py` | Multi-profile pooling |
| `network_interceptor.py` | Advanced request/response |

---

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
│  │  - Memory Integration                          │       │
│  │  - Form Builder     - Action Recorder          │       │
│  │  - Screenshots     - Webhooks                 │       │
│  │  - Session Pool    - Network Interceptor       │       │
│  └─────────────────────┬───────────────────────┘       │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────┐       │
│  │            Playwright (Chromium)            │       │
│  └──────────────────────────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

```env
HEADLESS=true
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080
DEFAULT_TIMEOUT=30000
SESSION_EXPIRY_HOURS=168
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
```

---

## Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Core Browser | ✅ |
| 1 | REST API | ✅ |
| 1 | Session Pool | ✅ |
| 2 | Memory Integration | ✅ |
| 2 | Form Builder | ✅ |
| 2 | Action Recorder | ✅ |
| 2 | Screenshot Analysis | ✅ |
| 3 | Webhooks | ✅ |
| 3 | Session Pool Pro | ✅ |
| 3 | Network Interceptor | ✅ |
