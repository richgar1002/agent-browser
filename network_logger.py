"""
Network Logger - Capture and analyze network traffic
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import config

class NetworkLogger:
    """Log network requests and responses"""
    
    def __init__(self):
        self.requests: List[Dict] = []
        self.responses: List[Dict] = []
        self._request_log = []
        self._response_log = []
    
    def log_request(self, data: Dict):
        """Log a request"""
        self.requests.append(data)
        self._request_log.append(data)
        
        # Trim to keep memory usage reasonable
        max_entries = 1000
        if len(self._request_log) > max_entries:
            self._request_log = self._request_log[-max_entries:]
    
    def log_response(self, data: Dict):
        """Log a response"""
        self.responses.append(data)
        self._response_log.append(data)
        
        max_entries = 1000
        if len(self._response_log) > max_entries:
            self._response_log = self._response_log[-max_entries:]
    
    def get_log(self) -> Dict:
        """Get all logged data"""
        return {
            "requests": self._request_log,
            "responses": self._response_log,
            "count": {
                "requests": len(self._request_log),
                "responses": len(self._response_log)
            }
        }
    
    def get_requests_by_url(self, url_pattern: str) -> List[Dict]:
        """Get requests matching URL pattern"""
        return [r for r in self._request_log if url_pattern in r.get("url", "")]
    
    def get_api_calls(self) -> List[Dict]:
        """Get API calls (JSON requests/responses)"""
        api_calls = []
        
        for req in self._request_log:
            url = req.get("url", "")
            if any(ext in url for ext in ['/api/', '/graphql', '.json', '/v1/']):
                # Find matching response
                matching_resps = [r for r in self._response_log if r.get("url") == url]
                api_calls.append({
                    "request": req,
                    "response": matching_resps[0] if matching_resps else None
                })
        
        return api_calls
    
    def get_failed_requests(self) -> List[Dict]:
        """Get failed requests (4xx, 5xx)"""
        failed = []
        
        for resp in self._response_log:
            status = resp.get("status", 0)
            if status >= 400:
                # Find matching request
                url = resp.get("url")
                matching_reqs = [r for r in self._request_log if r.get("url") == url]
                failed.append({
                    "request": matching_reqs[0] if matching_reqs else {},
                    "response": resp
                })
        
        return failed
    
    def export_har(self, filepath: str = None) -> str:
        """Export as HAR format"""
        if filepath is None:
            filepath = str(config.LOGS_DIR / f"network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.har")
        
        har = {
            "log": {
                "version": "1.2",
                "creator": {"name": "AgentBrowser", "version": "1.0"},
                "entries": []
            }
        }
        
        # Build HAR entries
        for req in self._request_log:
            entry = {
                "request": {
                    "method": req.get("method", "GET"),
                    "url": req.get("url", ""),
                    "headers": [{"name": k, "value": v} for k, v in req.get("headers", {}).items()]
                },
                "response": {"status": 0, "statusText": "", "headers": [], "content": {}},
                "time": 0
            }
            
            # Find response
            for resp in self._response_log:
                if resp.get("url") == req.get("url"):
                    entry["response"]["status"] = resp.get("status", 0)
                    break
            
            har["log"]["entries"].append(entry)
        
        with open(filepath, "w") as f:
            json.dump(har, f, indent=2)
        
        return filepath
    
    def clear(self):
        """Clear all logs"""
        self.requests = []
        self.responses = []
        self._request_log = []
        self._response_log = []
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            "total_requests": len(self._request_log),
            "total_responses": len(self._response_log),
            "api_calls": len(self.get_api_calls()),
            "failed_requests": len(self.get_failed_requests()),
            "unique_urls": len(set(r.get("url", "") for r in self._request_log))
        }
