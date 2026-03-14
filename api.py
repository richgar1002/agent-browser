"""
Agent Browser API
REST API to control the browser remotely
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
import base64

from browser import create_browser, AgentBrowser
import config

app = FastAPI(title="Agent Browser API")

# Global browser instance
browser: Optional[AgentBrowser] = None

# Models
class NavigateInput(BaseModel):
    url: str
    wait_until: str = "load"
    timeout: int = None

class ClickInput(BaseModel):
    selector: str

class FillInput(BaseModel):
    selector: str
    value: str

class EvaluateInput(BaseModel):
    javascript: str

class ScreenshotInput(BaseModel):
    full_page: bool = False

class InterceptInput(BaseModel):
    url_pattern: str
    action: str = "abort"  # abort, fulfill, continue

# Startup
@app.on_event("startup")
async def startup():
    global browser
    browser = create_browser("default")
    await browser.start()

@app.on_event("shutdown")
async def shutdown():
    global browser
    if browser:
        await browser.close()

# Navigation
@app.post("/go_to")
async def navigate(input: NavigateInput):
    global browser
    await browser.go_to(input.url, input.wait_until, input.timeout)
    return {"status": "ok", "url": browser.current_url}

@app.post("/reload")
async def reload():
    global browser
    await browser.reload()
    return {"status": "ok"}

@app.post("/back")
async def back():
    global browser
    await browser.back()
    return {"status": "ok"}

@app.post("/forward")
async def forward():
    global browser
    await browser.forward()
    return {"status": "ok"}

# Waiting
@app.post("/wait_for_selector")
async def wait_for_selector(selector: str, timeout: int = None):
    global browser
    await browser.wait_for_selector(selector, timeout)
    return {"status": "ok"}

@app.post("/wait_for_load")
async def wait_for_load(state: str = "networkidle"):
    global browser
    await browser.wait_for_load_state(state)
    return {"status": "ok"}

# Interaction
@app.post("/click")
async def click(input: ClickInput):
    global browser
    await browser.click(input.selector)
    return {"status": "ok"}

@app.post("/fill")
async def fill(input: FillInput):
    global browser
    await browser.fill(input.selector, input.value)
    return {"status": "ok"}

@app.post("/type")
async def type_text(input: FillInput, delay: int = 50):
    global browser
    await browser.type_text(input.selector, input.value, delay)
    return {"status": "ok"}

# Content extraction
@app.post("/get_text")
async def get_text(selector: str = None):
    global browser
    text = await browser.get_text(selector)
    return {"text": text}

@app.post("/get_html")
async def get_html(selector: str = None):
    global browser
    html = await browser.get_inner_html(selector) if selector else await browser.get_text()
    return {"html": html}

@app.post("/get_all_text")
async def get_all_text(selector: str):
    global browser
    texts = await browser.get_all_text(selector)
    return {"texts": texts}

@app.post("/get_attribute")
async def get_attribute(selector: str, attribute: str):
    global browser
    value = await browser.get_attribute(selector, attribute)
    return {"value": value}

# JavaScript
@app.post("/evaluate")
async def evaluate(input: EvaluateInput):
    global browser
    result = await browser.evaluate(input.javascript)
    return {"result": result}

# Screenshots
@app.post("/screenshot")
async def screenshot(input: ScreenshotInput):
    global browser
    path = await browser.screenshot(full_page=input.full_page)
    return {"path": path}

@app.post("/screenshot_base64")
async def screenshot_base64(input: ScreenshotInput):
    global browser
    b64 = await browser.screenshot_base64(input.full_page)
    return {"image": b64}

# Network
@app.get("/network")
async def get_network_log():
    global browser
    return browser.get_network_log()

@app.post("/network/clear")
async def clear_network_log():
    global browser
    browser.clear_network_log()
    return {"status": "ok"}

@app.post("/network/block")
async def block_requests(patterns: List[str]):
    global browser
    await browser.block_requests(patterns)
    return {"status": "ok"}

# Session
@app.post("/session/save")
async def save_session():
    global browser
    await browser.save_session()
    return {"status": "ok"}

@app.get("/session/list")
async def list_sessions():
    from session_manager import SessionManager
    sm = SessionManager()
    return sm.list_sessions()

@app.delete("/session/{name}")
async def delete_session(name: str):
    from session_manager import SessionManager
    sm = SessionManager()
    sm.delete_session(name)
    return {"status": "ok"}

# Browser control
@app.post("/close")
async def close():
    global browser
    await browser.close()
    await browser.start()
    return {"status": "ok"}

@app.get("/url")
async def get_url():
    global browser
    return {"url": browser.current_url}

# Health
@app.get("/health")
async def health():
    return {"status": "healthy", "browser": "running" if browser else "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
