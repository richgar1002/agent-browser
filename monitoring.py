"""
Performance & Monitoring Module
- Caching
- Connection Pooling
- Performance Metrics
- Health Checks
- Logging
"""
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import threading
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === CACHING ===

@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0


class PageCache:
    """
    LRU Cache for web pages
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: deque = deque()
        self._lock = threading.Lock()
        
        # Stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _make_key(self, url: str, options: dict = None) -> str:
        """Create cache key"""
        data = url
        if options:
            data += str(sorted(options.items()))
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, url: str, options: dict = None) -> Optional[Any]:
        """Get cached value"""
        key = self._make_key(url, options)
        
        with self._lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            now = time.time()
            
            # Check expiration
            if now > entry.expires_at:
                del self.cache[key]
                self.access_order.remove(key)
                self.stats['misses'] += 1
                return None
            
            # Update stats
            entry.hits += 1
            self.stats['hits'] += 1
            
            # Move to end of access order
            self.access_order.remove(key)
            self.access_order.append(key)
            
            return entry.value
    
    def set(self, url: str, value: Any, options: dict = None, ttl: int = None):
        """Set cached value"""
        key = self._make_key(url, options)
        ttl = ttl or self.ttl_seconds
        now = time.time()
        
        with self._lock:
            # Evict if full
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()
            
            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl
            )
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
    
    def _evict_oldest(self):
        """Evict oldest entry"""
        if self.access_order:
            oldest_key = self.access_order.popleft()
            if oldest_key in self.cache:
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self) -> Dict:
        """Get cache stats"""
        with self._lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self.stats['evictions']
            }


# === PERFORMANCE METRICS ===

@dataclass
class PerformanceMetric:
    """Performance metric"""
    name: str
    value: float
    unit: str
    timestamp: float


class PerformanceTracker:
    """
    Track performance metrics
    """
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.metrics: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        
        # Counters
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, List[float]] = {}
    
    def record(self, name: str, value: float, unit: str = ""):
        """Record a metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time()
        )
        
        with self._lock:
            self.metrics.append(metric)
    
    def increment(self, name: str, value: int = 1):
        """Increment a counter"""
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + value
    
    def start_timer(self, name: str):
        """Start a timer"""
        with self._lock:
            if name not in self.timers:
                self.timers[name] = []
            self.timers[name].append(time.time())
    
    def stop_timer(self, name: str) -> Optional[float]:
        """Stop timer and return duration"""
        with self._lock:
            if name not in self.timers or not self.timers[name]:
                return None
            
            start_time = self.timers[name].pop()
            duration = time.time() - start_time
            
            # Record metric
            self.metrics.append(PerformanceMetric(
                name=f"{name}_duration",
                value=duration,
                unit="seconds",
                timestamp=time.time()
            ))
            
            return duration
    
    def get_stats(self) -> Dict:
        """Get performance stats"""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Filter recent metrics
            recent = [m for m in self.metrics if m.timestamp > cutoff]
            
            # Calculate averages
            by_name: Dict[str, List[float]] = {}
            for m in recent:
                if m.name not in by_name:
                    by_name[m.name] = []
                by_name[m.name].append(m.value)
            
            averages = {
                name: sum(values) / len(values)
                for name, values in by_name.items()
            }
            
            return {
                'counters': dict(self.counters),
                'averages': averages,
                'total_metrics': len(recent)
            }
    
    def reset(self):
        """Reset metrics"""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.timers.clear()


# === HEALTH CHECKS ===

class HealthChecker:
    """
    Health monitoring for browser sessions
    """
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_check: Dict[str, datetime] = {}
        self.check_history: deque = deque(maxlen=100)
        self._lock = threading.Lock()
    
    def register(self, name: str, check_fn: callable):
        """Register a health check"""
        self.checks[name] = check_fn
    
    async def check_all(self) -> Dict:
        """Run all health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_fn in self.checks.items():
            try:
                start = time.time()
                result = await check_fn() if asyncio.iscoroutinefunction(check_fn) else check_fn()
                duration = time.time() - start
                
                healthy = result.get('healthy', True) if isinstance(result, dict) else result
                
                results[name] = {
                    'healthy': healthy,
                    'duration_ms': int(duration * 1000),
                    'details': result if isinstance(result, dict) else None
                }
                
                if not healthy:
                    overall_healthy = False
                    
            except Exception as e:
                results[name] = {
                    'healthy': False,
                    'error': str(e)
                }
                overall_healthy = False
        
        # Record history
        with self._lock:
            self.check_history.append({
                'timestamp': datetime.now().isoformat(),
                'overall_healthy': overall_healthy,
                'checks': results
            })
        
        return {
            'healthy': overall_healthy,
            'checks': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get check history"""
        with self._lock:
            return list(self.check_history)[-limit:]


# === ACTION LOGGING ===

class ActionLogger:
    """
    Log all browser actions
    """
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.logs: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        
        # Log levels
        self.levels = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }
        
        self.min_level = 'INFO'
    
    def log(
        self,
        level: str,
        action: str,
        details: Dict = None,
        session: str = None
    ):
        """Log an action"""
        if self.levels.get(level, 20) < self.levels.get(self.min_level, 20):
            return
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'action': action,
            'details': details or {},
            'session': session
        }
        
        with self._lock:
            self.logs.append(entry)
        
        # Also log to standard logger
        getattr(logger, level.lower(), logger.info)(f"{action}: {details}")
    
    def debug(self, action: str, details: Dict = None, session: str = None):
        self.log('DEBUG', action, details, session)
    
    def info(self, action: str, details: Dict = None, session: str = None):
        self.log('INFO', action, details, session)
    
    def warning(self, action: str, details: Dict = None, session: str = None):
        self.log('WARNING', action, details, session)
    
    def error(self, action: str, details: Dict = None, session: str = None):
        self.log('ERROR', action, details, session)
    
    def get_logs(
        self,
        level: str = None,
        action: str = None,
        session: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get filtered logs"""
        with self._lock:
            logs = list(self.logs)
        
        # Filter
        if level:
            logs = [l for l in logs if l['level'] == level]
        if action:
            logs = [l for l in logs if action.lower() in l['action'].lower()]
        if session:
            logs = [l for l in logs if l['session'] == session]
        
        return logs[-limit:]


# === ALERTS ===

class AlertManager:
    """
    Manage alerts for failure scenarios
    """
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.handlers: List[callable] = []
        self._lock = threading.Lock()
    
    def add_handler(self, handler: callable):
        """Add alert handler"""
        self.handlers.append(handler)
    
    async def trigger(
        self,
        level: str,
        title: str,
        message: str,
        details: Dict = None
    ):
        """Trigger an alert"""
        alert = {
            'id': len(self.alerts) + 1,
            'timestamp': datetime.now().isoformat(),
            'level': level,  # info, warning, error, critical
            'title': title,
            'message': message,
            'details': details or {},
            'acknowledged': False
        }
        
        with self._lock:
            self.alerts.append(alert)
        
        # Notify handlers
        for handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        return alert
    
    def get_alerts(
        self,
        level: str = None,
        acknowledged: bool = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get alerts"""
        with self._lock:
            alerts = list(self.alerts)
        
        if level:
            alerts = [a for a in alerts if a['level'] == level]
        if acknowledged is not None:
            alerts = [a for a in alerts if a['acknowledged'] == acknowledged]
        
        return alerts[-limit:]
    
    def acknowledge(self, alert_id: int) -> bool:
        """Acknowledge an alert"""
        with self._lock:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['acknowledged'] = True
                    return True
        return False


# === FACTORY ===

import asyncio

def create_monitoring() -> Dict:
    """Create monitoring components"""
    return {
        'cache': PageCache(max_size=100, ttl_seconds=300),
        'metrics': PerformanceTracker(),
        'health': HealthChecker(),
        'logger': ActionLogger(),
        'alerts': AlertManager()
    }
