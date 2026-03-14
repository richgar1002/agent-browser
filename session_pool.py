"""
Session Pool - Manage multiple browser contexts
"""
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

import playwright.async_api as pw
from playwright.async_api import async_playwright, Browser, BrowserContext

from enhanced_browser import create_enhanced_browser, EnhancedAgentBrowser

logger = logging.getLogger(__name__)

@dataclass
class PooledSession:
    """A session in the pool"""
    name: str
    browser: EnhancedAgentBrowser
    created_at: datetime
    last_used: datetime
    in_use: bool = False
    tags: List[str] = field(default_factory=list)

class SessionPool:
    """Pool of browser sessions for fast switching"""
    
    def __init__(self, max_sessions: int = 5, idle_timeout_minutes: int = 30):
        self.max_sessions = max_sessions
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.sessions: Dict[str, PooledSession] = {}
        self.playwright = None
        self.browser: Optional[Browser] = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Initialize the pool"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        logger.info("Session pool started")
    
    async def acquire(self, session_name: str = "default", tags: List[str] = None) -> EnhancedAgentBrowser:
        """Get a browser session from the pool"""
        async with self._lock:
            # Check if session exists and is available
            if session_name in self.sessions:
                session = self.sessions[session_name]
                
                if session.in_use:
                    # Wait for session to be available
                    raise SessionInUseError(f"Session '{session_name}' is in use")
                
                if self._is_idle(session):
                    # Recreate browser for idle session
                    await self._recreate_session(session)
                
                session.in_use = True
                session.last_used = datetime.now()
                return session.browser
            
            # Create new session
            if len(self.sessions) >= self.max_sessions:
                # Evict oldest idle session
                await self._evict_oldest()
            
            browser = create_enhanced_browser(session_name)
            await browser.start()
            
            session = PooledSession(
                name=session_name,
                browser=browser,
                created_at=datetime.now(),
                last_used=datetime.now(),
                in_use=True,
                tags=tags or []
            )
            
            self.sessions[session_name] = session
            logger.info(f"Created new session: {session_name}")
            
            return browser
    
    async def release(self, session_name: str):
        """Release a session back to the pool"""
        async with self._lock:
            if session_name in self.sessions:
                self.sessions[session_name].in_use = False
                self.sessions[session_name].last_used = datetime.now()
                logger.debug(f"Released session: {session_name}")
    
    async def _recreate_session(self, session: PooledSession):
        """Recreate browser for session"""
        try:
            await session.browser.close()
        except:
            pass
        
        session.browser = create_enhanced_browser(session.name)
        await session.browser.start()
        session.last_used = datetime.now()
        logger.info(f"Recreated session: {session.name}")
    
    async def _evict_oldest(self):
        """Evict oldest idle session"""
        oldest = None
        oldest_time = datetime.now()
        
        for name, session in self.sessions.items():
            if not session.in_use and session.last_used < oldest_time:
                oldest = name
                oldest_time = session.last_used
        
        if oldest:
            await self._destroy_session(oldest)
    
    async def _destroy_session(self, session_name: str):
        """Destroy a session"""
        if session_name in self.sessions:
            try:
                await self.sessions[session_name].browser.close()
            except:
                pass
            del self.sessions[session_name]
            logger.info(f"Destroyed session: {session_name}")
    
    def _is_idle(self, session: PooledSession) -> bool:
        """Check if session is idle"""
        return datetime.now() - session.last_used > self.idle_timeout
    
    async def cleanup(self):
        """Clean up all sessions"""
        async with self._lock:
            for session_name in list(self.sessions.keys()):
                await self._destroy_session(session_name)
            
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Session pool cleaned up")
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        return {
            "total_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "sessions": {
                name: {
                    "in_use": s.in_use,
                    "created": s.created_at.isoformat(),
                    "last_used": s.last_used.isoformat(),
                    "idle": self._is_idle(s),
                    "tags": s.tags
                }
                for name, s in self.sessions.items()
            }
        }
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


class SessionInUseError(Exception):
    """Session is already in use"""
    pass


# Global pool instance
_pool: Optional[SessionPool] = None

def get_session_pool() -> SessionPool:
    """Get global session pool"""
    global _pool
    if _pool is None:
        _pool = SessionPool()
    return _pool
