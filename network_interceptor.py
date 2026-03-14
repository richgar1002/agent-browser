"""
Network Interception - Advanced network monitoring and blocking
"""
import json
import re
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import config

@dataclass
class BlockRule:
    """Rule for blocking requests"""
    pattern: str
    reason: str = "manual"
    regex: bool = False

@dataclass
class RequestLog:
    """Logged request"""
    url: str
    method: str
    headers: Dict
    timestamp: datetime
    status: Optional[int] = None
    response_size: Optional[int] = None
    blocked: bool = False
    block_reason: Optional[str] = None

class NetworkInterceptor:
    """Advanced network interception with blocking"""
    
    # Default ad/tracker domains to block
    DEFAULT_BLOCKLIST = [
        # Ads
        r".*\.doubleclick\.net",
        r".*\.googlesyndication\.com",
        r".*\.googleadservices\.com",
        r".*\.adnxs\.com",
        r".*\.adsrvr\.org",
        r".*\.adform\.net",
        r".*\.taboola\.com",
        r".*\.outbrain\.com",
        r".*\.criteo\.com",
        r".*\.pubmatic\.com",
        r".*\.rubiconproject\.com",
        
        # Trackers
        r".*\.google-analytics\.com",
        r".*\.googletagmanager\.com",
        r".*\.hotjar\.com",
        r".*\.mixpanel\.com",
        r".*\.segment\.io",
        r".*\.segment\.com",
        r".*\.amplitude\.com",
        r".*\.newrelic\.com",
        r".*\.fullstory\.com",
        
        # Social (optional)
        # r".*\.facebook\.com/plugins",
        # r".*\.twitter\.com/widgets",
        
        # Malware
        r".*\.malware-check\.disconnect\.me",
    ]
    
    def __init__(self):
        self.requests: List[RequestLog] = []
        self.block_rules: List[BlockRule] = []
        self._setup_default_blocklist()
        self.custom_handler: Optional[Callable] = None
    
    def _setup_default_blocklist(self):
        """Setup default ad/tracker blocklist"""
        for pattern in self.DEFAULT_BLOCKLIST:
            self.block_rules.append(BlockRule(
                pattern=pattern,
                reason="ad/tracker"
            ))
    
    def add_block_rule(self, pattern: str, reason: str = "manual", regex: bool = False):
        """Add a blocking rule"""
        self.block_rules.append(BlockRule(
            pattern=pattern,
            reason=reason,
            regex=regex
        ))
    
    def remove_block_rule(self, pattern: str):
        """Remove a blocking rule"""
        self.block_rules = [r for r in self.block_rules if r.pattern != pattern]
    
    def should_block(self, url: str) -> tuple[bool, Optional[str]]:
        """Check if URL should be blocked"""
        for rule in self.block_rules:
            if rule.regex:
                if re.search(rule.pattern, url):
                    return True, rule.reason
            else:
                if rule.pattern in url:
                    return True, rule.reason
        
        return False, None
    
    def log_request(self, url: str, method: str, headers: Dict) -> RequestLog:
        """Log a request"""
        blocked, reason = self.should_block(url)
        
        log = RequestLog(
            url=url,
            method=method,
            headers=headers,
            timestamp=datetime.now(),
            blocked=blocked,
            block_reason=reason
        )
        
        self.requests.append(log)
        
        # Keep last 5000
        if len(self.requests) > 5000:
            self.requests = self.requests[-5000:]
        
        return log
    
    def log_response(self, url: str, status: int, size: int):
        """Log a response"""
        for req in reversed(self.requests):
            if req.url == url and req.status is None:
                req.status = status
                req.response_size = size
                break
    
    def get_requests(self, method: str = None, status: int = None, 
                     blocked: bool = None, url_pattern: str = None) -> List[Dict]:
        """Get filtered requests"""
        results = self.requests
        
        if method:
            results = [r for r in results if r.method == method]
        if status:
            results = [r for r in results if r.status == status]
        if blocked is not None:
            results = [r for r in results if r.blocked == blocked]
        if url_pattern:
            results = [r for r in results if url_pattern in r.url]
        
        return [self._to_dict(r) for r in results]
    
    def get_blocked(self) -> List[Dict]:
        """Get all blocked requests"""
        return [self._to_dict(r) for r in self.requests if r.blocked]
    
    def get_api_calls(self) -> List[Dict]:
        """Get API calls (JSON responses)"""
        api_calls = []
        
        for req in self.requests:
            if req.status and 200 <= req.status < 300:
                if any(ext in req.url for ext in ['/api/', '/graphql', '.json', '/v1/']):
                    api_calls.append(self._to_dict(req))
        
        return api_calls
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        total = len(self.requests)
        blocked = len([r for r in self.requests if r.blocked])
        api_calls = len(self.get_api_calls())
        failed = len([r for r in self.requests if r.status and r.status >= 400])
        
        # Count by method
        methods = {}
        for r in self.requests:
            methods[r.method] = methods.get(r.method, 0) + 1
        
        # Count by status
        statuses = {}
        for r in self.requests:
            if r.status:
                statuses[r.status] = statuses.get(r.status, 0) + 1
        
        return {
            "total_requests": total,
            "blocked_requests": blocked,
            "api_calls": api_calls,
            "failed_requests": failed,
            "by_method": methods,
            "by_status": statuses
        }
    
    def export_json(self, filepath: str = None) -> str:
        """Export to JSON"""
        if filepath is None:
            filepath = str(config.LOGS_DIR / f"network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        data = [self._to_dict(r) for r in self.requests]
        
        with open(filepath, "w") as f:
            json.dump({
                "exported_at": datetime.now().isoformat(),
                "summary": self.get_summary(),
                "requests": data
            }, f, indent=2)
        
        return filepath
    
    def clear(self):
        """Clear all logs"""
        self.requests = []
    
    def _to_dict(self, req: RequestLog) -> Dict:
        """Convert to dict"""
        return {
            "url": req.url,
            "method": req.method,
            "headers": dict(req.headers),
            "timestamp": req.timestamp.isoformat(),
            "status": req.status,
            "response_size": req.response_size,
            "blocked": req.blocked,
            "block_reason": req.block_reason
        }


# Instance for import
interceptor = NetworkInterceptor()
