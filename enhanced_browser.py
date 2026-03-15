"""
Agent Browser - Enhanced Version
Complete integration of all modules
"""
import asyncio
import base64
import json
import uuid
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

import playwright.async_api as pw
from playwright.async_api import async_playwright, Browser, Page, Request, Response

import config
from network_logger import NetworkLogger
from session_manager import SessionManager

# Import all new modules
from memory_integration import BrowserMemory, PageSummary, create_browser_memory
from form_builder import FormBuilder, create_form_builder
from action_recorder import ActionRecorder, ActionType, create_action_recorder
from screenshot_analyzer import ScreenshotAnalyzer, create_screenshot_analyzer
from webhook_manager import WebhookManager, TriggerType, create_webhook_manager
from session_pool_manager import SessionPool, create_session_pool
from network_interceptor import NetworkInterceptor, create_network_interceptor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class EnhancedAgentBrowser:
    """
    AI-first headless browser with all integrations
    """
    
    def __init__(self, session_name: str = "default", user_id: str = None):
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
        self.last_html = None
        
        # === INTEGRATED MODULES ===
        
        # Memory
        self.memory: BrowserMemory = None
        self._memory_enabled = True
        
        # Form Builder
        storage_path = str(Path(config.DATA_DIR) / "forms")
        os.makedirs(storage_path, exist_ok=True)
        self.form_builder: FormBuilder = create_form_builder(storage_path)
        
        # Action Recorder
        workflows_path = str(Path(config.DATA_DIR) / "workflows")
        os.makedirs(workflows_path, exist_ok=True)
        self.recorder: ActionRecorder = create_action_recorder(workflows_path)
        
        # Screenshot Analyzer
        self.analyzer = create_screenshot_analyzer()
        
        # Webhooks
        webhooks_path = str(Path(config.DATA_DIR) / "webhooks")
        os.makedirs(webhooks_path, exist_ok=True)
        self.webhooks: WebhookManager = create_webhook_manager(webhooks_path)
        
        # Session Pool
        self.session_pool = create_session_pool(min_sessions=2, max_sessions=10)
        
        # Network Interceptor
        self.interceptor = create_network_interceptor()
        
        logger.info("Enhanced browser initialized")
    
    async def start(self, headless: bool = None, memory_enabled: bool = True):
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
            self.page.on("request", self._on_request)
        if config.LOG_RESPONSES:
            self.page.on("response", self._on_response)
        
        # Initialize memory if enabled
        if memory_enabled and self._memory_enabled:
            try:
                self.memory = create_browser_memory()
                logger.info("Memory integration enabled")
            except Exception as e:
                logger.warning(f"Memory not available: {e}")
        
        # Enable network interceptor
        self.interceptor.enable()
        
        return self
    
    async def _on_request(self, request: Request):
        """Log network requests"""
        self.network_logger.log_request({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "timestamp": datetime.now().isoformat()
        })
        
        # Check webhook triggers
        self.webhooks.check_triggers(
            TriggerType.URL_CHANGE,
            request.url,
            {"method": request.method}
        )
    
    async def _on_response(self, response: Response):
        """Log network responses"""
        self.network_logger.log_response({
            "url": response.url,
            "status": response.status,
            "timestamp": datetime.now().isoformat()
        })
    
    # === NAVIGATION ===
    
    async def go_to(self, url: str, wait_until: str = "load", timeout: int = None):
        """Navigate to URL"""
        timeout = timeout or config.NAVIGATION_TIMEOUT
        self.current_url = url
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        
        # Check webhooks for URL change
        self.webhooks.check_triggers(TriggerType.URL_CHANGE, url)
        
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
    
    # === WAITING ===
    
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
    
    # === INTERACTION ===
    
    async def click(self, selector: str):
        """Click element"""
        await self.page.click(selector)
        
        # Record action if recording
        if self.recorder.is_recording:
            self.recorder.record_click(selector)
        
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
        
        # Record action if recording
        if self.recorder.is_recording:
            self.recorder.record_type(selector, value)
        
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
    
    # === CONTENT ===
    
    async def get_text(self, selector: str = None) -> str:
        """Get text content"""
        if selector:
            return await self.page.text_content(selector) or ""
        return await self.page.content()
    
    async def get_html(self) -> str:
        """Get page HTML"""
        self.last_html = await self.page.content()
        return self.last_html
    
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
    
    # === JAVASCRIPT ===
    
    async def evaluate(self, js: str):
        """Execute JavaScript"""
        return await self.page.evaluate(js)
    
    async def evaluate_async(self, js: str):
        """Execute async JavaScript"""
        return await self.page.evaluate_async(js)
    
    # === SCREENSHOTS ===
    
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
    
    # === MEMORY INTEGRATION ===
    
    async def save_to_memory(self, tags: List[str] = None) -> bool:
        """Save current page to memory"""
        if not self.memory:
            logger.warning("Memory not initialized")
            return False
        
        try:
            # Get page content
            title = await self.page.title()
            content = await self.get_text()[:10000]
            
            page = PageSummary(
                url=self.current_url,
                title=title,
                content=content,
                screenshot=self.last_screenshot,
                tags=tags
            )
            
            result = self.memory.save_page(page)
            
            if result:
                # Check webhooks
                self.webhooks.check_triggers(
                    TriggerType.CONTENT_CHANGE,
                    title,
                    {"url": self.current_url, "saved": True}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save to memory: {e}")
            return False
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memory"""
        if not self.memory:
            return []
        return self.memory.search_memory(query, limit)
    
    # === FORM BUILDER ===
    
    def find_and_fill_form(self, data: Dict[str, str]) -> bool:
        """Find form for current URL and fill it"""
        form = self.form_builder.find_form_by_url(self.current_url)
        if not form:
            logger.warning(f"No form found for {self.current_url}")
            return False
        
        fill_data = self.form_builder.fill_form_data(form.id, data)
        
        # Would need to be called in async context
        # This is sync helper for planning
        logger.info(f"Would fill: {fill_data}")
        return True
    
    # === ACTION RECORDER ===
    
    def start_recording(self, name: str, description: str = ""):
        """Start recording actions"""
        self.recorder.start_recording(name, description)
        logger.info(f"Started recording: {name}")
    
    def stop_recording(self):
        """Stop recording"""
        workflow = self.recorder.stop_recording()
        logger.info(f"Stopped recording: {workflow.name if workflow else 'none'}")
        return workflow
    
    # === SCREENSHOT ANALYSIS ===
    
    async def analyze_screenshot(self) -> Dict:
        """Analyze last screenshot"""
        if not self.last_screenshot:
            # Take one
            await self.screenshot()
        
        result = self.analyzer.analyze(self.last_screenshot)
        
        # Check webhooks for content
        if result.text:
            self.webhooks.check_triggers(
                TriggerType.TEXT_MATCHES,
                result.text[:200],
                {"screenshot": self.last_screenshot}
            )
        
        return {
            "text": result.text,
            "buttons": result.buttons,
            "links": result.links,
            "summary": result.summary,
            "elements": result.elements
        }
    
    # === NETWORK ===
    
    def get_network_log(self) -> Dict:
        """Get network request/response log"""
        return self.network_logger.get_log()
    
    def clear_network_log(self):
        """Clear network log"""
        self.network_logger.clear()
    
    def get_network_metrics(self) -> Dict:
        """Get network metrics"""
        return self.interceptor.get_metrics()
    
    async def intercept_requests(self, handler):
        """Enable request interception"""
        await self.page.route("**/*", handler)
        self.network_interception_enabled = True
    
    async def block_requests(self, patterns: List[str]):
        """Block specific requests"""
        for pattern in patterns:
            await self.page.route(pattern, lambda route: route.abort())
    
    # === COOKIES & STORAGE ===
    
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
    
    # === SESSION ===
    
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
        # Save session
        await self.save_session()
        
        # Close components
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        # Disable interceptor
        self.interceptor.disable()
        
        logger.info("Browser closed")
    
    # === CONTEXT MANAGER ===
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_browser(session_name: str = "default", user_id: str = None) -> EnhancedAgentBrowser:
    """Factory function"""
    return EnhancedAgentBrowser(session_name, user_id)
