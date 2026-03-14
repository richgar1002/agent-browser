"""
Agent Browser - Enhanced Browser Core with Error Handling
"""
import asyncio
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

import playwright.async_api as pw
from playwright.async_api import async_playwright, Browser, Page, Error as PlaywrightError

import config
from browser import AgentBrowser as BaseAgentBrowser
from network_logger import NetworkLogger
from session_manager import SessionManager

logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 30.0

@dataclass
class BrowserError:
    """Structured error information"""
    error_type: str
    message: str
    selector: Optional[str] = None
    url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    recoverable: bool = True

class EnhancedAgentBrowser(BaseAgentBrowser):
    """Browser with error handling and retry logic"""
    
    def __init__(self, session_name: str = "default", retry_config: RetryConfig = None):
        super().__init__(session_name)
        self.retry_config = retry_config or RetryConfig()
        self.error_log = []
        self._closed = False
    
    async def start(self, headless: bool = None):
        """Start browser with error handling"""
        try:
            await super().start(headless)
            logger.info(f"Browser started for session: {self.session_name}")
        except Exception as e:
            error = self._create_error("BROWSER_START", str(e))
            self._log_error(error)
            raise BrowserStartError(str(e)) from e
    
    async def close(self):
        """Close browser gracefully"""
        if self._closed:
            return
        
        try:
            await super().close()
            logger.info(f"Browser closed for session: {self.session_name}")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self._closed = True
    
    async def go_to(self, url: str, wait_until: str = "load", timeout: int = None):
        """Navigate with retry logic"""
        return await self._with_retry(
            "goto",
            lambda: super().go_to(url, wait_until, timeout),
            {"url": url}
        )
    
    async def click(self, selector: str):
        """Click with retry"""
        return await self._with_retry(
            "click",
            lambda: super().click(selector),
            {"selector": selector}
        )
    
    async def fill(self, selector: str, value: str):
        """Fill with retry"""
        return await self._with_retry(
            "fill",
            lambda: super().fill(selector, value),
            {"selector": selector, "value": value}
        )
    
    async def wait_for_selector(self, selector: str, timeout: int = None):
        """Wait for selector with retry"""
        return await self._with_retry(
            "wait_for_selector",
            lambda: super().wait_for_selector(selector, timeout),
            {"selector": selector}
        )
    
    async def screenshot(self, path: str = None, full_page: bool = False) -> Optional[str]:
        """Take screenshot with error handling"""
        try:
            return await super().screenshot(path, full_page)
        except Exception as e:
            error = self._create_error("SCREENSHOT", str(e))
            self._log_error(error)
            logger.error(f"Screenshot failed: {e}")
            return None
    
    async def _with_retry(self, operation: str, func: Callable, context: dict = None):
        """Execute function with retry logic"""
        last_error = None
        delay = self.retry_config.initial_delay
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                result = await func()
                
                if attempt > 1:
                    logger.info(f"{operation} succeeded on attempt {attempt}")
                
                return result
                
            except PlaywrightError as e:
                last_error = e
                error_type = "PLAYWRIGHT_ERROR"
                recoverable = self._is_recoverable(str(e))
                
                error = self._create_error(error_type, str(e), context)
                error.recoverable = recoverable
                self._log_error(error)
                
                if not recoverable or attempt >= self.retry_config.max_attempts:
                    logger.error(f"{operation} failed after {attempt} attempts: {e}")
                    raise
                
                logger.warning(f"{operation} failed (attempt {attempt}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                delay = min(delay * self.retry_config.backoff_multiplier, self.retry_config.max_delay)
                
            except Exception as e:
                last_error = e
                error = self._create_error("UNKNOWN", str(e), context)
                self._log_error(error)
                raise
        
        raise last_error
    
    def _is_recoverable(self, error_msg: str) -> bool:
        """Determine if error is recoverable"""
        unrecoverable = [
            "Target closed",
            "Browser closed",
            "Context closed",
            "Navigation failed because",
            "net::ERR_"
        ]
        
        for pattern in unrecoverable:
            if pattern in error_msg:
                return False
        
        return True
    
    def _create_error(self, error_type: str, message: str, context: dict = None) -> BrowserError:
        """Create structured error"""
        return BrowserError(
            error_type=error_type,
            message=message,
            selector=context.get("selector") if context else None,
            url=context.get("url") if context else None
        )
    
    def _log_error(self, error: BrowserError):
        """Log error to history"""
        self.error_log.append(error)
        
        # Keep last 100 errors
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
    
    def get_error_log(self) -> list:
        """Get error history"""
        return [
            {
                "type": e.error_type,
                "message": e.message,
                "selector": e.selector,
                "url": e.url,
                "timestamp": e.timestamp.isoformat(),
                "recoverable": e.recoverable
            }
            for e in self.error_log
        ]
    
    def clear_error_log(self):
        """Clear error history"""
        self.error_log = []


class BrowserStartError(Exception):
    """Failed to start browser"""
    pass


class BrowserOperationError(Exception):
    """Browser operation failed"""
    pass


# Factory function
def create_enhanced_browser(session_name: str = "default") -> EnhancedAgentBrowser:
    """Factory for enhanced browser"""
    return EnhancedAgentBrowser(session_name)
