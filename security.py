"""
Security Middleware for Agent Browser API
- Authentication
- Rate Limiting
- Request Validation
- Content Security Policy
"""
import time
import hashlib
from functools import wraps
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === CONFIGURATION ===

class SecurityConfig:
    """Security configuration"""
    # API Key
    API_KEY = "your-secret-key-change-me"
    API_KEY_HASH = None  # Will be computed
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Request validation
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_URL_SCHEMES = ["http", "https"]
    BLOCKED_URL_PATTERNS = []
    
    # CSP
    CSP_ENABLED = True
    CSP_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    @classmethod
    def init(cls):
        """Initialize security config"""
        cls.API_KEY_HASH = hashlib.sha256(cls.API_KEY.encode()).hexdigest()


# === RATE LIMITING ===

@dataclass
class RateLimitInfo:
    """Rate limit tracking"""
    requests: List[float] = field(default_factory=list)
    blocked: bool = False
    block_until: float = 0


class RateLimiter:
    """Rate limiter using sliding window"""
    
    def __init__(self, requests: int = None, window: int = None):
        self.max_requests = requests or SecurityConfig.RATE_LIMIT_REQUESTS
        self.window = window or SecurityConfig.RATE_LIMIT_WINDOW
        self.clients: Dict[str, RateLimitInfo] = {}
    
    def check(self, client_id: str) -> tuple[bool, Dict]:
        """
        Check if request is allowed
        Returns: (allowed, info)
        """
        now = time.time()
        
        # Initialize if new client
        if client_id not in self.clients:
            self.clients[client_id] = RateLimitInfo()
        
        info = self.clients[client_id]
        
        # Check if blocked
        if info.blocked and now < info.block_until:
            return False, {
                "allowed": False,
                "blocked": True,
                "retry_after": int(info.block_until - now)
            }
        
        # Clear expired requests
        cutoff = now - self.window
        info.requests = [r for r in info.requests if r > cutoff]
        
        # Check limit
        if len(info.requests) >= self.max_requests:
            # Block for short period
            info.blocked = True
            info.block_until = now + 30  # Block for 30 seconds
            logger.warning(f"Rate limit exceeded for {client_id}")
            
            return False, {
                "allowed": False,
                "blocked": True,
                "retry_after": 30,
                "limit": self.max_requests,
                "window": self.window
            }
        
        # Allow request
        info.requests.append(now)
        
        return True, {
            "allowed": True,
            "remaining": self.max_requests - len(info.requests),
            "reset_in": self.window
        }
    
    def reset(self, client_id: str):
        """Reset rate limit for client"""
        if client_id in self.clients:
            self.clients[client_id] = RateLimitInfo()


# === AUTHENTICATION ===

class AuthManager:
    """API Key authentication"""
    
    def __init__(self):
        self.valid_keys: Dict[str, Dict] = {}
        self._init_default_keys()
    
    def _init_default_keys(self):
        """Initialize default API keys"""
        # Add default key
        self.add_key(
            key="secret",
            name="default",
            expires_days=365
        )
    
    def add_key(self, key: str, name: str, expires_days: int = None) -> str:
        """Add an API key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        self.valid_keys[key_hash] = {
            "name": name,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "requests": 0
        }
        
        return key_hash
    
    def verify_key(self, key: str) -> tuple[bool, Optional[Dict]]:
        """Verify API key"""
        if not key:
            return False, None
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        if key_hash not in self.valid_keys:
            return False, None
        
        key_info = self.valid_keys[key_hash]
        
        # Check expiration
        if key_info["expires_at"] and key_info["expires_at"] < datetime.now():
            return False, None
        
        # Update usage
        key_info["requests"] += 1
        
        return True, key_info
    
    def revoke_key(self, key: str):
        """Revoke an API key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self.valid_keys:
            del self.valid_keys[key_hash]


# === REQUEST VALIDATION ===

class RequestValidator:
    """Validate API requests"""
    
    @staticmethod
    def validate_url(url: str) -> tuple[bool, Optional[str]]:
        """Validate URL"""
        if not url:
            return False, "URL is required"
        
        if len(url) > 2048:
            return False, "URL too long"
        
        # Check scheme
        if not any(url.startswith(s + "://") for s in SecurityConfig.ALLOWED_URL_SCHEMES):
            return False, f"URL must use {' or '.join(SecurityConfig.ALLOWED_URL_SCHEMES)}"
        
        # Check blocked patterns
        for pattern in SecurityConfig.BLOCKED_URL_PATTERNS:
            if pattern in url:
                return False, "URL blocked"
        
        return True, None
    
    @staticmethod
    def validate_selector(selector: str) -> tuple[bool, Optional[str]]:
        """Validate CSS selector"""
        if not selector:
            return True, None  # Optional
        
        if len(selector) > 500:
            return False, "Selector too long"
        
        # Basic validation - no complex patterns that could cause ReDoS
        dangerous = ["<script", "javascript:", "onerror", "onclick"]
        for d in dangerous:
            if d in selector.lower():
                return False, f"Invalid selector"
        
        return True, None
    
    @staticmethod
    def validate_size(size: int) -> tuple[bool, Optional[str]]:
        """Validate data size"""
        if size > SecurityConfig.MAX_REQUEST_SIZE:
            return False, f"Request too large (max {SecurityConfig.MAX_REQUEST_SIZE // 1024 // 1024}MB)"
        
        return True, None
    
    @staticmethod
    def validate_json(data: dict, schema: dict) -> tuple[bool, List[str]]:
        """Validate JSON against schema"""
        errors = []
        
        for field, rules in schema.items():
            # Required
            if rules.get("required", False) and field not in data:
                errors.append(f"Missing required field: {field}")
                continue
            
            if field not in data:
                continue
            
            value = data[field]
            
            # Type check
            expected_type = rules.get("type")
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"{field} must be string")
            elif expected_type == "int" and not isinstance(value, int):
                errors.append(f"{field} must be integer")
            elif expected_type == "bool" and not isinstance(value, bool):
                errors.append(f"{field} must be boolean")
            
            # String constraints
            if isinstance(value, str):
                min_len = rules.get("min_length", 0)
                max_len = rules.get("max_length", 999999)
                if len(value) < min_len or len(value) > max_len:
                    errors.append(f"{field} length must be {min_len}-{max_len}")
        
        return len(errors) == 0, errors


# === CSP MIDDLEWARE ===

class CSPMiddleware:
    """Content Security Policy middleware"""
    
    def __init__(self, policy: str = None):
        self.policy = policy or SecurityConfig.CSP_POLICY
    
    def get_headers(self) -> Dict[str, str]:
        """Get CSP headers"""
        if not SecurityConfig.CSP_ENABLED:
            return {}
        
        return {
            "Content-Security-Policy": self.policy,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }


# === DECORATORS ===

def rate_limit(limiter: RateLimiter):
    """Decorator to apply rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            client_id = request.client.host if hasattr(request, 'client') else 'unknown'
            
            allowed, info = limiter.check(client_id)
            
            if not allowed:
                return {
                    "error": "Rate limit exceeded",
                    **info
                }
            
            result = await func(request, *args, **kwargs)
            
            # Add rate limit headers
            if hasattr(result, '__dict__'):
                result.rate_limit_remaining = info.get("remaining")
            
            return result
        
        return wrapper
    return decorator


def require_auth(auth: AuthManager):
    """Decorator to require authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # Get API key from header
            api_key = request.headers.get("X-Api-Key")
            
            if not api_key:
                return {"error": "API key required", "code": "AUTH_REQUIRED"}
            
            valid, info = auth.verify_key(api_key)
            
            if not valid:
                return {"error": "Invalid API key", "code": "AUTH_INVALID"}
            
            # Add to request
            request.auth = info
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# === INITIALIZE ===

def init_security():
    """Initialize security components"""
    SecurityConfig.init()
    
    rate_limiter = RateLimiter()
    auth_manager = AuthManager()
    validator = RequestValidator()
    csp = CSPMiddleware()
    
    return {
        "rate_limiter": rate_limiter,
        "auth_manager": auth_manager,
        "validator": validator,
        "csp": csp
    }
