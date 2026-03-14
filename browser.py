"""
Agent Browser - Core Engine
AI-first headless browser with session persistence
"""
import asyncio
import base64
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

import playwright.async_api as pw
from playwright.async_api import async_playwright, Browser, Page, Request, Response

import config
from network_logger import NetworkLogger
from session_manager import SessionManager

@dataclass
class BrowserSession:
    """Represents a browser session"""
    id: str
    name: str
    created_at: datetime
    last_used: datetime
    cookies: Dict = field(default_factory=dict)
    local_storage: Dict = field(default_factory=dict)
    session_storage: Dict = field(default_factory=dict)

class AgentBrowser:
    """AI-first headless browser"""
    
    def __init__(self, session_name: str = "default"):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[pw.Context] = None
        self.page: Optional[Page] = None
        
        self.session_name = session_name
        self.session_manager = SessionManager()
        
        # Network logging
        self.network_logger = NetworkLogger()
        self.network_interception_enabled = False
        
        # Current state
        self.current_url = ""
        self.last_screenshot = None
        
    async def start(self, headless: bool = None):
        """Start the browser"""
        headless = headless if headless is not None else config.HEADLESS
        
        self.playwright = await async_playwright().start()
        
        # Launch browser
        launch_options = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        
        # Proxy if configured
        if config.PROXY_SERVER:
            launch_options["proxy"] = {
                "server": config.PROXY_SERVER,
                "username": config.PROXY_USERNAME,
                "password": config.PROXY_PASSWORD
            }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with viewport
        context_options = {
            "viewport": {"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
            "user_agent": config.USER_AGENT,
            "ignore_https_errors": True,
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Load existing session if available
        session = self.session_manager.load_session(self.session_name)
        if session and session.get("cookies"):
            await self.context.add_cookies(session["cookies"])
        
        # Create page
        self.page = await self.context.new_page()
        
        # Set up network logging
        if config.LOG_REQUESTS:
            await self.page.on("request", self._on_request)
        if config.LOG_RESPONSES:
            await self.page.on("response", self._on_response)
        
        return self
    
    async def _on_request(self, request: Request):
        """Log network requests"""
        self.network_logger.log_request({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "timestamp": datetime.now().isoformat()
        })
    
    async def _on_response(self, response: Response):
        """Log network responses"""
        self.network_logger.log_response({
            "url": response.url,
            "status": response.status,
            "timestamp": datetime.now().isoformat()
        })
    
    # Navigation
    async def go_to(self, url: str, wait_until: str = "load", timeout: int = None):
        """Navigate to URL"""
        timeout = timeout or config.NAVIGATION_TIMEOUT
        self.current_url = url
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        return self
    
    async def reload(self, wait_until: str = "load"):
        """Reload current page"""
        await self.page.reload(wait_until=wait_until)
        return self
    
    async def back(self):
        """Go back"""
        await self.page.go_back()
        return self
    
    async def forward(self):
        """Go forward"""
        await self.page.go_forward()
        return self
    
    # Waiting
    async def wait_for_selector(self, selector: str, timeout: int = None):
        """Wait for element to appear"""
        timeout = timeout or config.DEFAULT_TIMEOUT
        await self.page.wait_for_selector(selector, timeout=timeout)
        return self
    
    async def wait_for_load_state(self, state: str = "networkidle"):
        """Wait for page to load"""
        await self.page.wait_for_load_state(state)
        return self
    
    async def wait_for_function(self, js_function: str, timeout: int = None):
        """Wait for JavaScript function to return true"""
        timeout = timeout or config.DEFAULT_TIMEOUT
        await self.page.wait_for_function(js_function, timeout=timeout)
        return self
    
    # Interaction
    async def click(self, selector: str):
        """Click element"""
        await self.page.click(selector)
        return self
    
    async def double_click(self, selector: str):
        """Double click element"""
        await self.page.dblclick(selector)
        return self
    
    async def hover(self, selector: str):
        """Hover over element"""
        await self.page.hover(selector)
        return self
    
    async def fill(self, selector: str, value: str):
        """Fill input field"""
        await self.page.fill(selector, value)
        return self
    
    async def type_text(self, selector: str, text: str, delay: int = 50):
        """Type text with delay (human-like)"""
        await self.page.type(selector, text, delay=delay)
        return self
    
    async def press_key(self, selector: str, key: str):
        """Press key on element"""
        await self.page.press(selector, key)
        return self
    
    async def select_option(self, selector: str, value: str):
        """Select dropdown option"""
        await self.page.select_option(selector, value)
        return self
    
    # Content extraction
    async def get_text(self, selector: str = None) -> str:
        """Get text content"""
        if selector:
            return await self.page.text_content(selector) or ""
        return await self.page.content()
    
    async def get_attribute(self, selector: str, attribute: str) -> str:
        """Get element attribute"""
        return await self.page.get_attribute(selector, attribute) or ""
    
    async def get_inner_html(self, selector: str) -> str:
        """Get inner HTML"""
        return await self.page.inner_html(selector)
    
    async def get_all_text(self, selector: str) -> List[str]:
        """Get text from all matching elements"""
        elements = await self.page.query_selector_all(selector)
        return [await e.text_content() or "" for e in elements]
    
    async def get_elements(self, selector: str) -> List:
        """Get all matching elements"""
        return await self.page.query_selector_all(selector)
    
    # Evaluation
    async def evaluate(self, js: str):
        """Execute JavaScript"""
        return await self.page.evaluate(js)
    
    async def evaluate_async(self, js: str):
        """Execute async JavaScript"""
        return await self.page.evaluate_async(js)
    
    # Screenshots
    async def screenshot(self, path: str = None, full_page: bool = False) -> Optional[str]:
        """Take screenshot"""
        if path is None:
            path = str(config.SCREENSHOTS_DIR / f"{uuid.uuid4().hex}.png")
        
        await self.page.screenshot(path=path, full_page=full_page)
        self.last_screenshot = path
        return path
    
    async def screenshot_base64(self, full_page: bool = False) -> str:
        """Get screenshot as base64"""
        return await self.page.screenshot(full_page=full_page, encoding="base64")
    
    # Network
    def get_network_log(self) -> Dict:
        """Get network request/response log"""
        return self.network_logger.get_log()
    
    def clear_network_log(self):
        """Clear network log"""
        self.network_logger.clear()
    
    async def intercept_requests(self, handler):
        """Enable request interception"""
        await self.page.route("**/*", handler)
        self.network_interception_enabled = True
    
    async def block_requests(self, patterns: List[str]):
        """Block specific requests"""
        for pattern in patterns:
            await self.page.route(pattern, lambda route: route.abort())
    
    # Cookies & Storage
    async def get_cookies(self) -> List[Dict]:
        """Get all cookies"""
        return await self.context.cookies()
    
    async def set_cookies(self, cookies: List[Dict]):
        """Set cookies"""
        await self.context.add_cookies(cookies)
    
    async def get_local_storage(self) -> Dict:
        """Get localStorage"""
        return await self.page.evaluate("() => JSON.stringify(localStorage)")
    
    async def set_local_storage(self, data: Dict):
        """Set localStorage"""
        await self.page.evaluate(f"() => {{ localStorage.setObject({json.dumps(data)}); }}")
    
    # Session management
    async def save_session(self):
        """Save current session"""
        cookies = await self.get_cookies()
        local_storage = await self.get_local_storage()
        
        session_data = {
            "id": self.session_name,
            "cookies": cookies,
            "local_storage": local_storage,
            "saved_at": datetime.now().isoformat()
        }
        
        self.session_manager.save_session(self.session_name, session_data)
    
    async def close(self):
        """Close browser"""
        # Save session before closing
        await self.save_session()
        
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    # Context manager
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_browser(session_name: str = "default") -> AgentBrowser:
    """Factory function"""
    return AgentBrowser(session_name)
