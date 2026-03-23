"""
Session Pool Manager
Rotate browser instances, manage profiles, proxy support
"""
import logging
import uuid
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Browser session states"""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class BrowserProfile:
    """Browser profile configuration"""
    id: str
    name: str
    proxy: str = None  # proxy URL
    user_agent: str = None
    timezone: str = "UTC"
    language: str = "en-US"
    viewport: Dict[str, int] = None  # width, height
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {'width': 1920, 'height': 1080}


@dataclass
class BrowserSession:
    """A browser session instance"""
    id: str
    profile: BrowserProfile
    state: SessionState = SessionState.IDLE
    created_at: str = None
    last_used: str = None
    use_count: int = 0
    error: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class SessionPool:
    """
    Manage a pool of browser sessions
    Supports: profiles, proxy rotation, session pooling
    """
    
    def __init__(
        self,
        min_sessions: int = 2,
        max_sessions: int = 10,
        idle_timeout: int = 300  # seconds
    ):
        self.min_sessions = min_sessions
        self.max_sessions = max_sessions
        self.idle_timeout = idle_timeout
        
        self.sessions: Dict[str, BrowserSession] = {}
        self.profiles: Dict[str, BrowserProfile] = {}
        self._lock = threading.Lock()
        
        # Stats
        self.stats = {
            'total_requests': 0,
            'active_sessions': 0,
            'errors': 0
        }
    
    # --- Profiles ---
    
    def create_profile(
        self,
        name: str,
        proxy: str = None,
        user_agent: str = None,
        **kwargs
    ) -> BrowserProfile:
        """Create a browser profile"""
        profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        
        profile = BrowserProfile(
            id=profile_id,
            name=name,
            proxy=proxy,
            user_agent=user_agent,
            **kwargs
        )
        
        self.profiles[profile_id] = profile
        logger.info(f"Created profile: {name}")
        
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get a profile"""
        return self.profiles.get(profile_id)
    
    def list_profiles(self) -> List[BrowserProfile]:
        """List all profiles"""
        return list(self.profiles.values())
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile"""
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False
    
    # --- Sessions ---
    
    def create_session(self, profile_id: str = None) -> BrowserSession:
        """Create a new browser session"""
        with self._lock:
            if len(self.sessions) >= self.max_sessions:
                # Try to get an idle session
                idle = self._get_idle_session()
                if idle:
                    return idle
                raise Exception("Max sessions reached")
            
            profile = None
            if profile_id and profile_id in self.profiles:
                profile = self.profiles[profile_id]
            elif self.profiles:
                profile = list(self.profiles.values())[0]
            else:
                # Default profile
                profile = BrowserProfile(
                    id="default",
                    name="Default"
                )
            
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            session = BrowserSession(
                id=session_id,
                profile=profile
            )
            
            self.sessions[session_id] = session
            logger.info(f"Created session: {session_id}")
            
            return session
    
    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a session"""
        return self.sessions.get(session_id)
    
    def release_session(self, session_id: str):
        """Release a session back to the pool"""
        session = self.get_session(session_id)
        if session:
            session.state = SessionState.IDLE
            session.last_used = datetime.now().isoformat()
            logger.debug(f"Released session: {session_id}")
    
    def close_session(self, session_id: str):
        """Close and remove a session"""
        session = self.get_session(session_id)
        if session:
            session.state = SessionState.CLOSED
            # In production, would close actual browser
            del self.sessions[session_id]
            logger.info(f"Closed session: {session_id}")
    
    def _get_idle_session(self) -> Optional[BrowserSession]:
        """Get an idle session from the pool"""
        now = datetime.now()
        
        for session in self.sessions.values():
            if session.state == SessionState.IDLE:
                # Check timeout
                if session.last_used:
                    last_used = datetime.fromisoformat(session.last_used)
                    elapsed = (now - last_used).total_seconds()
                    
                    if elapsed > self.idle_timeout:
                        # Session expired, close it
                        self.close_session(session.id)
                        continue
                
                return session
        
        return None
    
    def acquire_session(self, profile_id: str = None) -> BrowserSession:
        """Acquire a session from the pool"""
        self.stats['total_requests'] += 1
        
        # Try to get idle session with matching profile
        for session in self.sessions.values():
            if session.state == SessionState.IDLE:
                if profile_id is None or session.profile.id == profile_id:
                    session.state = SessionState.ACTIVE
                    session.last_used = datetime.now().isoformat()
                    session.use_count += 1
                    self.stats['active_sessions'] = sum(
                        1 for s in self.sessions.values() 
                        if s.state == SessionState.ACTIVE
                    )
                    return session
        
        # Create new session
        try:
            session = self.create_session(profile_id)
            session.state = SessionState.ACTIVE
            session.use_count = 1
            self.stats['active_sessions'] += 1
            return session
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to acquire session: {e}")
            raise
    
    # --- Proxy ---
    
    def rotate_proxy(self, session_id: str, proxy: str) -> bool:
        """Rotate proxy for a session"""
        session = self.get_session(session_id)
        if session:
            session.profile.proxy = proxy
            logger.info(f"Rotated proxy for {session_id}: {proxy}")
            return True
        return False
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation (if configured)"""
        # Could implement proxy rotation logic here
        # For now, returns None
        return None
    
    # --- Stats ---
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        states = {}
        for state in SessionState:
            states[state.value] = sum(
                1 for s in self.sessions.values() 
                if s.state == state
            )
        
        return {
            **self.stats,
            'sessions': states,
            'total_sessions': len(self.sessions),
            'profiles': len(self.profiles)
        }
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions with details"""
        return [
            {
                'id': s.id,
                'profile': s.profile.name,
                'state': s.state.value,
                'use_count': s.use_count,
                'created': s.created_at,
                'last_used': s.last_used
            }
            for s in self.sessions.values()
        ]
    
    # --- Cleanup ---
    
    def cleanup_idle(self):
        """Clean up idle sessions beyond minimum"""
        with self._lock:
            idle_count = sum(
                1 for s in self.sessions.values() 
                if s.state == SessionState.IDLE
            )
            
            if idle_count <= self.min_sessions:
                return
            
            # Close oldest idle sessions
            sessions_to_close = idle_count - self.min_sessions
            
            for session in sorted(
                self.sessions.values(),
                key=lambda s: s.last_used or s.created_at
            ):
                if session.state == SessionState.IDLE and sessions_to_close > 0:
                    self.close_session(session.id)
                    sessions_to_close -= 1
    
    def health_check(self) -> Dict:
        """Check health of session pool"""
        active = self.stats['active_sessions']
        total = len(self.sessions)
        
        return {
            'healthy': total > 0 and active < total,
            'active': active,
            'total': total,
            'errors': self.stats['errors']
        }


def create_session_pool(
    min_sessions: int = 2,
    max_sessions: int = 10
) -> SessionPool:
    """Factory function"""
    return SessionPool(min_sessions, max_sessions)
