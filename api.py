"""
Agent Browser API - Enhanced + Security
Complete REST API with all features and security
"""
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
import base64
import asyncio
from contextvars import ContextVar

from enhanced_browser import create_browser, EnhancedAgentBrowser
from security import (
    SecurityConfig, RateLimiter, AuthManager, 
    RequestValidator, CSPMiddleware, init_security
)
import config

# Initialize security
security = init_security()
rate_limiter = security["rate_limiter"]
auth_manager = security["auth_manager"]
validator = security["validator"]
csp_middleware = security["csp"]

app = FastAPI(title="Agent Browser API - Enhanced")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_browser_instances: Dict[str, EnhancedAgentBrowser] = {}
_browser_locks: Dict[str, asyncio.Lock] = {}
_browser_manager_lock = asyncio.Lock()
_current_browser: ContextVar[Optional[EnhancedAgentBrowser]] = ContextVar(
    "current_browser",
    default=None
)


class BrowserProxy:
    """Request-scoped browser proxy backed by ContextVar."""

    def _current(self) -> EnhancedAgentBrowser:
        browser = _current_browser.get()
        if browser is None:
            raise RuntimeError(
                "No browser bound to this request. Provide X-Session-Name and use a browser endpoint."
            )
        return browser

    def __getattr__(self, name):
        return getattr(self._current(), name)


browser: BrowserProxy = BrowserProxy()


async def _get_or_create_browser(session_name: str) -> EnhancedAgentBrowser:
    """Get an existing browser for a session or create one lazily."""
    existing = _browser_instances.get(session_name)
    if existing:
        return existing

    async with _browser_manager_lock:
        existing = _browser_instances.get(session_name)
        if existing:
            return existing

        instance = create_browser(session_name)
        await instance.start(memory_enabled=True)
        _browser_instances[session_name] = instance
        _browser_locks[session_name] = asyncio.Lock()
        return instance


# === MIDDLEWARE ===

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Apply security middleware"""
    # Rate limiting
    client_id = request.client.host if request.client else "unknown"
    allowed, rate_info = rate_limiter.check(client_id)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": rate_info.get("retry_after", 60)
            }
        )

    # API key enforcement (except health/docs and preflight)
    public_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
    if (
        SecurityConfig.AUTH_REQUIRED
        and request.method != "OPTIONS"
        and request.url.path not in public_paths
    ):
        api_key = request.headers.get("X-Api-Key", "")
        valid, _ = auth_manager.verify_key(api_key)
        if not valid:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"}
            )
    
    # Paths that do not require a browser context.
    no_browser_paths = {
        "/health", "/docs", "/redoc", "/openapi.json", "/auth/key", "/auth/keys"
    }

    if request.url.path in no_browser_paths:
        response = await call_next(request)
    else:
        session_name = request.headers.get("X-Session-Name", "default").strip() or "default"
        request.state.session_name = session_name
        browser_instance = await _get_or_create_browser(session_name)
        request.state.browser = browser_instance

        session_lock = _browser_locks[session_name]
        token = _current_browser.set(browser_instance)
        try:
            async with session_lock:
                response = await call_next(request)
        finally:
            _current_browser.reset(token)

    # CSP headers
    for header, value in csp_middleware.get_headers().items():
        response.headers[header] = value
    
    # Rate limit headers
    response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
    response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset_in", 60))
    
    return response


# === MODELS ===

class NavigateInput(BaseModel):
    url: str
    wait_until: str = "load"
    timeout: int = None
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        valid, err = validator.validate_url(v)
        if not valid:
            raise ValueError(err)
        return v


class ClickInput(BaseModel):
    selector: str
    
    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v):
        valid, err = validator.validate_selector(v)
        if not valid:
            raise ValueError(err)
        return v


class FillInput(BaseModel):
    selector: str
    value: str
    
    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v):
        valid, err = validator.validate_selector(v)
        if not valid:
            raise ValueError(err)
        return v


class EvaluateInput(BaseModel):
    javascript: str
    
    @field_validator('javascript')
    @classmethod
    def validate_js(cls, v):
        # Basic JS validation
        dangerous = ["<script", "eval(", "Function("]
        for d in dangerous:
            if d.lower() in v.lower():
                raise ValueError("Potentially dangerous JavaScript")
        return v


class ScreenshotInput(BaseModel):
    full_page: bool = False


class MemoryInput(BaseModel):
    tags: List[str] = None


class SearchInput(BaseModel):
    query: str
    limit: int = 5


class WebhookInput(BaseModel):
    name: str
    url: str
    trigger_type: str
    trigger_value: str
    headers: Dict = {}


class FormInput(BaseModel):
    name: str
    url_pattern: str


class FormFieldInput(BaseModel):
    form_id: str
    field_name: str
    selector: str
    field_type: str = "text"


class WorkflowInput(BaseModel):
    name: str
    description: str = ""


# === AUTH ENDPOINTS ===

@app.post("/auth/key")
async def create_api_key(name: str, expires_days: int = 365):
    """Create a new API key"""
    import secrets
    key = secrets.token_urlsafe(32)
    key_hash = auth_manager.add_key(key, name, expires_days)
    
    return {
        "api_key": key,
        "name": name,
        "expires_days": expires_days,
        "message": "Save this key - it won't be shown again"
    }


@app.get("/auth/keys")
async def list_keys():
    """List API keys (without secrets)"""
    return {
        "keys": [
            {
                "name": info["name"],
                "created_at": info["created_at"].isoformat(),
                "expires_at": info["expires_at"].isoformat() if info["expires_at"] else None,
                "requests": info["requests"]
            }
            for info in auth_manager.valid_keys.values()
        ]
    }


# === STARTUP ===

@app.on_event("startup")
async def startup():
    if SecurityConfig.AUTH_REQUIRED and len(auth_manager.valid_keys) == 0:
        raise RuntimeError(
            "AUTH_REQUIRED is true but no API keys are configured. "
            "Set AGENT_BROWSER_API_KEY or set AUTH_REQUIRED=false for dev only."
        )


@app.on_event("shutdown")
async def shutdown():
    for browser_instance in list(_browser_instances.values()):
        try:
            await browser_instance.close()
        except Exception:
            pass
    _browser_instances.clear()
    _browser_locks.clear()


# === NAVIGATION ===

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


# === WAITING ===

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


# === INTERACTION ===

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


# === CONTENT ===

@app.post("/get_text")
async def get_text(selector: str = None):
    global browser
    text = await browser.get_text(selector)
    return {"text": text}


@app.post("/get_html")
async def get_html(selector: str = None):
    global browser
    html = await browser.get_inner_html(selector) if selector else await browser.get_html()
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


# === JAVASCRIPT ===

@app.post("/evaluate")
async def evaluate(input: EvaluateInput):
    global browser
    result = await browser.evaluate(input.javascript)
    return {"result": result}


# === SCREENSHOTS ===

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


@app.post("/analyze")
async def analyze_screenshot():
    global browser
    result = await browser.analyze_screenshot()
    return result


# === MEMORY ===

@app.post("/memory/save")
async def save_to_memory(input: MemoryInput):
    global browser
    tags = input.tags if input.tags else None
    result = await browser.save_to_memory(tags)
    return {"status": "ok", "saved": result}


@app.post("/memory/search")
async def search_memory(input: SearchInput):
    global browser
    results = browser.search_memory(input.query, input.limit)
    return {"results": results, "count": len(results)}


@app.get("/memory/pages")
async def get_saved_pages(limit: int = 20):
    global browser
    if browser.memory:
        pages = browser.memory.get_saved_pages(limit)
        return {"pages": pages, "count": len(pages)}
    return {"pages": [], "count": 0}


# === NETWORK ===

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


@app.get("/network/metrics")
async def get_network_metrics():
    global browser
    return browser.get_network_metrics()


# === FORMS ===

@app.get("/forms")
async def list_forms():
    global browser
    forms = browser.form_builder.list_forms()
    return {"forms": [f.to_dict() for f in forms]}


@app.post("/forms")
async def create_form(input: FormInput):
    global browser
    form = browser.form_builder.create_form(input.name, input.url_pattern)
    return form.to_dict()


@app.post("/forms/field")
async def add_form_field(input: FormFieldInput):
    global browser
    result = browser.form_builder.add_field(
        input.form_id,
        input.field_name,
        input.selector,
        input.field_type
    )
    return {"status": "ok", "result": result}


# === RECORDING ===

@app.post("/record/start")
async def start_recording(input: WorkflowInput):
    global browser
    browser.start_recording(input.name, input.description)
    return {"status": "recording", "name": input.name}


@app.post("/record/stop")
async def stop_recording():
    global browser
    workflow = browser.stop_recording()
    if workflow:
        return {"status": "stopped", "workflow": workflow.to_dict()}
    return {"status": "stopped", "workflow": None}


@app.get("/workflows")
async def list_workflows():
    global browser
    workflows = browser.recorder.list_workflows()
    return {"workflows": [w.to_dict() for w in workflows]}


# === WEBHOOKS ===

@app.get("/webhooks")
async def list_webhooks():
    global browser
    webhooks = browser.webhooks.list_webhooks()
    return {"webhooks": [w.to_dict() for w in webhooks]}


@app.post("/webhooks")
async def create_webhook(input: WebhookInput):
    global browser
    from webhook_manager import TriggerType
    
    webhook = browser.webhooks.create_webhook(
        name=input.name,
        url=input.url,
        trigger_type=TriggerType(input.trigger_type),
        trigger_value=input.trigger_value,
        headers=input.headers
    )
    return webhook.to_dict()


@app.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    global browser
    result = browser.webhooks.test_webhook(webhook_id)
    return {"status": "ok", "fired": result}


@app.get("/webhooks/logs")
async def get_webhook_logs(webhook_id: str = None, limit: int = 50):
    global browser
    logs = browser.webhooks.get_logs(webhook_id, limit)
    return {"logs": [{"id": l.webhook_id, "event": l.event.value, "success": l.success} for l in logs]}


# === SESSION POOL ===

@app.get("/pool/stats")
async def get_pool_stats():
    global browser
    return browser.session_pool.get_stats()


@app.get("/pool/sessions")
async def list_pool_sessions():
    global browser
    return {"sessions": browser.session_pool.list_sessions()}


@app.get("/pool/profiles")
async def list_profiles():
    global browser
    return {"profiles": [p.__dict__ for p in browser.session_pool.list_profiles()]}


# === SESSION ===

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


# === BROWSER CONTROL ===

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


# === SECURITY ===

@app.get("/security/config")
async def security_config():
    """Get security configuration (non-sensitive)"""
    return {
        "rate_limit": {
            "requests": rate_limiter.max_requests,
            "window": rate_limiter.window
        },
        "csp_enabled": SecurityConfig.CSP_ENABLED,
        "max_request_size": SecurityConfig.MAX_REQUEST_SIZE
    }


# === HEALTH ===

@app.get("/health")
async def health():
    active_sessions = len(_browser_instances)
    any_browser = next(iter(_browser_instances.values()), None)
    return {
        "status": "healthy",
        "browser": "running" if active_sessions > 0 else "stopped",
        "memory": any_browser.memory is not None if any_browser else False,
        "sessions": active_sessions,
        "features": {
            "memory": True,
            "forms": True,
            "recorder": True,
            "webhooks": True,
            "pool": True
        },
        "security": {
            "rate_limiting": True,
            "csp": SecurityConfig.CSP_ENABLED,
            "keys": len(auth_manager.valid_keys)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
