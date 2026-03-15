"""
Network Interceptor & Modifier
Request/response modification, API mocking, performance metrics
"""
import logging
import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestMethod(Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class Request:
    """Captured HTTP request"""
    id: str
    method: RequestMethod
    url: str
    headers: Dict[str, str]
    body: str = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc
    
    @property
    def path(self) -> str:
        return urlparse(self.url).path


@dataclass
class Response:
    """Captured HTTP response"""
    request_id: str
    status: int
    headers: Dict[str, str]
    body: str = None
    duration_ms: float = 0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class MockRule:
    """Rule for mocking responses"""
    def __init__(
        self,
        url_pattern: str,
        method: RequestMethod = None,
        response_status: int = 200,
        response_body: str = None,
        response_headers: Dict[str, str] = None,
        delay_ms: int = 0
    ):
        self.url_pattern = url_pattern
        self.method = method
        self.response_status = response_status
        self.response_body = response_body
        self.response_headers = response_headers or {'Content-Type': 'application/json'}
        self.delay_ms = delay_ms
    
    def matches(self, request: Request) -> bool:
        """Check if this rule matches the request"""
        if self.method and request.method != self.method:
            return False
        
        return self.url_pattern in request.url


class NetworkInterceptor:
    """
    Intercept, modify, and mock HTTP requests/responses
    """
    
    def __init__(self):
        self.requests: List[Request] = []
        self.responses: List[Response] = []
        self.mock_rules: List[MockRule] = []
        self.request_callbacks: List[Callable] = []
        self.response_callbacks: List[Callable] = []
        
        self._lock = threading.Lock()
        self._enabled = False
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'total_bytes': 0,
            'avg_duration_ms': 0,
            'by_domain': {},
            'by_endpoint': {}
        }
    
    def enable(self):
        """Enable interception"""
        self._enabled = True
        logger.info("Network interception enabled")
    
    def disable(self):
        """Disable interception"""
        self._enabled = False
        logger.info("Network interception disabled")
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    # --- Capture ---
    
    def capture_request(self, method: str, url: str, headers: Dict = None, body: str = None) -> str:
        """Capture an outgoing request"""
        if not self._enabled:
            return None
        
        request = Request(
            id=f"req_{len(self.requests)}",
            method=RequestMethod(method),
            url=url,
            headers=headers or {},
            body=body
        )
        
        with self._lock:
            self.requests.append(request)
            self.metrics['total_requests'] += 1
        
        # Update metrics
        self._update_metrics(request)
        
        # Run callbacks
        for callback in self.request_callbacks:
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Request callback error: {e}")
        
        # Check for mock
        mock = self._check_mock(request)
        if mock:
            return mock
        
        return None  # Continue with real request
    
    def capture_response(
        self,
        request_id: str,
        status: int,
        headers: Dict = None,
        body: str = None,
        duration_ms: float = 0
    ):
        """Capture a response"""
        if not self._enabled:
            return
        
        response = Response(
            request_id=request_id,
            status=status,
            headers=headers or {},
            body=body,
            duration_ms=duration_ms
        )
        
        with self._lock:
            self.responses.append(response)
        
        # Update metrics
        if body:
            self.metrics['total_bytes'] += len(body)
        
        # Run callbacks
        for callback in self.response_callbacks:
            try:
                callback(response)
            except Exception as e:
                logger.error(f"Response callback error: {e}")
    
    # --- Mocking ---
    
    def add_mock_rule(self, rule: MockRule):
        """Add a mock rule"""
        self.mock_rules.append(rule)
        logger.info(f"Added mock rule: {rule.url_pattern}")
    
    def remove_mock_rule(self, url_pattern: str):
        """Remove mock rules matching pattern"""
        self.mock_rules = [r for r in self.mock_rules if r.url_pattern != url_pattern]
    
    def clear_mock_rules(self):
        """Clear all mock rules"""
        self.mock_rules = []
    
    def _check_mock(self, request: Request) -> Optional[Dict]:
        """Check if request should be mocked"""
        for rule in self.mock_rules:
            if rule.matches(request):
                # Apply delay if specified
                if rule.delay_ms > 0:
                    time.sleep(rule.delay_ms / 1000)
                
                return {
                    'status': rule.response_status,
                    'body': rule.response_body,
                    'headers': rule.response_headers,
                    'mocked': True
                }
        
        return None
    
    def mock_api(
        self,
        url_pattern: str,
        response_body: Any,
        method: RequestMethod = None,
        status: int = 200,
        delay_ms: int = 0
    ):
        """Quick mock setup"""
        body_str = json.dumps(response_body) if isinstance(response_body, (dict, list)) else response_body
        
        rule = MockRule(
            url_pattern=url_pattern,
            method=method,
            response_status=status,
            response_body=body_str,
            delay_ms=delay_ms
        )
        
        self.add_mock_rule(rule)
    
    # --- Modification ---
    
    RequestModifier = Callable[[Request], Optional[Request]]
    ResponseModifier = Callable[[Response], Optional[Response]]
    
    def on_request(self, callback: RequestModifier):
        """Add request modifier callback"""
        self.request_callbacks.append(callback)
    
    def on_response(self, callback: ResponseModifier):
        """Add response modifier callback"""
        self.response_callbacks.append(callback)
    
    # --- Metrics ---
    
    def _update_metrics(self, request: Request):
        """Update performance metrics"""
        # By domain
        domain = request.domain
        if domain not in self.metrics['by_domain']:
            self.metrics['by_domain'][domain] = {'count': 0, 'avg_duration': 0}
        self.metrics['by_domain'][domain]['count'] += 1
        
        # By endpoint
        path = request.path
        if path not in self.metrics['by_endpoint']:
            self.metrics['by_endpoint'][path] = {'count': 0, 'avg_duration': 0}
        self.metrics['by_endpoint'][path]['count'] += 1
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        return {
            **self.metrics,
            'requests': len(self.requests),
            'responses': len(self.responses),
            'mock_rules': len(self.mock_rules)
        }
    
    def get_requests(
        self,
        domain: str = None,
        method: RequestMethod = None,
        limit: int = 100
    ) -> List[Request]:
        """Get captured requests"""
        requests = self.requests
        
        if domain:
            requests = [r for r in requests if domain in r.domain]
        
        if method:
            requests = [r for r in requests if r.method == method]
        
        return requests[-limit:]
    
    def get_responses(
        self,
        status: int = None,
        limit: int = 100
    ) -> List[Response]:
        """Get captured responses"""
        responses = self.responses
        
        if status:
            responses = [r for r in responses if r.status == status]
        
        return responses[-limit:]
    
    def clear(self):
        """Clear captured data"""
        with self._lock:
            self.requests.clear()
            self.responses.clear()
            logger.info("Cleared captured data")


def create_network_interceptor() -> NetworkInterceptor:
    """Factory function"""
    return NetworkInterceptor()
