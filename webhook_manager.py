"""
Webhook System for Browser
Trigger actions on page changes, content, events
"""
import logging
import time
import hashlib
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of webhook triggers"""
    URL_CHANGE = "url_change"
    CONTENT_CHANGE = "content_change"
    ELEMENT_APPEARS = "element_appears"
    ELEMENT_DISAPPEARS = "element_disappears"
    TEXT_MATCHES = "text_matches"
    TITLE_CHANGES = "title_changes"
    REQUEST_MATCHES = "request_matches"
    RESPONSE_MATCHES = "response_matches"


class WebhookEvent(Enum):
    """Webhook event types"""
    TRIGGERED = "triggered"
    ERROR = "error"
    TEST = "test"


@dataclass
class Webhook:
    """A webhook definition"""
    id: str
    name: str
    url: str  # Webhook destination URL
    trigger_type: TriggerType
    trigger_value: str  # What to match
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'trigger_type': self.trigger_type.value,
            'trigger_value': self.trigger_value,
            'headers': self.headers,
            'enabled': self.enabled,
            'created_at': self.created_at
        }


@dataclass
class WebhookLog:
    """Log of webhook execution"""
    webhook_id: str
    event: WebhookEvent
    timestamp: str
    payload: Dict = field(default_factory=dict)
    response: str = None
    success: bool = True
    error: str = None


class WebhookManager:
    """
    Manage webhooks for browser events
    """
    
    WEBHOOKS_FILE = "webhooks.json"
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.webhooks: Dict[str, Webhook] = {}
        self.logs: List[WebhookLog] = []
        self.listeners: Dict[TriggerType, List[Callable]] = {}
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WEBHOOKS_FILE}"
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for wh_data in data.get('webhooks', []):
                trigger_type = TriggerType(wh_data['trigger_type'])
                self.webhooks[wh_data['id']] = Webhook(
                    id=wh_data['id'],
                    name=wh_data['name'],
                    url=wh_data['url'],
                    trigger_type=trigger_type,
                    trigger_value=wh_data['trigger_value'],
                    headers=wh_data.get('headers', {}),
                    enabled=wh_data.get('enabled', True),
                    created_at=wh_data.get('created_at')
                )
                
        except FileNotFoundError:
            logger.info("No webhooks file found")
        except Exception as e:
            logger.error(f"Error loading webhooks: {e}")
    
    def _save_webhooks(self):
        """Save webhooks to storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WEBHOOKS_FILE}"
            data = {
                'webhooks': [wh.to_dict() for wh in self.webhooks.values()]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving webhooks: {e}")
    
    # --- CRUD ---
    
    def create_webhook(
        self,
        name: str,
        url: str,
        trigger_type: TriggerType,
        trigger_value: str,
        headers: Dict[str, str] = None
    ) -> Webhook:
        """Create a new webhook"""
        webhook_id = f"wh_{hashlib.md5(f'{name}{time.time()}'.encode()).hexdigest()[:8]}"
        
        webhook = Webhook(
            id=webhook_id,
            name=name,
            url=url,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            headers=headers or {}
        )
        
        self.webhooks[webhook_id] = webhook
        self._save_webhooks()
        
        logger.info(f"Created webhook: {name}")
        return webhook
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID"""
        return self.webhooks.get(webhook_id)
    
    def list_webhooks(self, enabled_only: bool = False) -> List[Webhook]:
        """List all webhooks"""
        webhooks = list(self.webhooks.values())
        if enabled_only:
            webhooks = [w for w in webhooks if w.enabled]
        return webhooks
    
    def update_webhook(
        self,
        webhook_id: str,
        name: str = None,
        url: str = None,
        enabled: bool = None
    ) -> Optional[Webhook]:
        """Update a webhook"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None
        
        if name:
            webhook.name = name
        if url:
            webhook.url = url
        if enabled is not None:
            webhook.enabled = enabled
        
        self._save_webhooks()
        return webhook
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self._save_webhooks()
            return True
        return False
    
    def toggle_webhook(self, webhook_id: str) -> bool:
        """Toggle webhook enabled/disabled"""
        webhook = self.get_webhook(webhook_id)
        if webhook:
            webhook.enabled = not webhook.enabled
            self._save_webhooks()
            return True
        return False
    
    # --- Triggering ---
    
    def check_triggers(self, event_type: TriggerType, value: str, context: Dict = None) -> List[Webhook]:
        """Check if any webhooks should trigger"""
        triggered = []
        context = context or {}
        
        for webhook in self.webhooks.values():
            if not webhook.enabled:
                continue
            
            if webhook.trigger_type != event_type:
                continue
            
            # Check trigger condition
            should_trigger = False
            
            if event_type == TriggerType.URL_CHANGE:
                should_trigger = webhook.trigger_value in value
            elif event_type == TriggerType.TEXT_MATCHES:
                should_trigger = webhook.trigger_value.lower() in value.lower()
            elif event_type == TriggerType.TITLE_CHANGES:
                should_trigger = webhook.trigger_value.lower() in value.lower()
            elif event_type == TriggerType.CONTENT_CHANGE:
                should_trigger = webhook.trigger_value in str(context.get('content', ''))
            
            if should_trigger:
                triggered.append(webhook)
                # Fire asynchronously
                threading.Thread(
                    target=self._fire_webhook,
                    args=(webhook, event_type, value, context)
                ).start()
        
        return triggered
    
    def _fire_webhook(self, webhook: Webhook, event_type: TriggerType, value: str, context: Dict):
        """Fire a webhook"""
        import requests
        
        payload = {
            'event': event_type.value,
            'trigger_value': webhook.trigger_value,
            'matched_value': value,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        log = WebhookLog(
            webhook_id=webhook.id,
            event=WebhookEvent.TRIGGERED,
            timestamp=datetime.now().isoformat(),
            payload=payload
        )
        
        try:
            response = requests.post(
                webhook.url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    **webhook.headers
                },
                timeout=10
            )
            
            log.response = response.text
            log.success = response.status_code < 400
            
            logger.info(f"Webhook fired: {webhook.name} - {response.status_code}")
            
        except Exception as e:
            log.success = False
            log.error = str(e)
            logger.error(f"Webhook failed: {webhook.name} - {e}")
        
        self.logs.append(log)
    
    def test_webhook(self, webhook_id: str) -> bool:
        """Test a webhook"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False
        
        self._fire_webhook(webhook, TriggerType.TEXT_MATCHES, "test", {'test': True})
        return True
    
    def get_logs(self, webhook_id: str = None, limit: int = 50) -> List[WebhookLog]:
        """Get webhook execution logs"""
        logs = self.logs
        if webhook_id:
            logs = [l for l in logs if l.webhook_id == webhook_id]
        return logs[-limit:]


def create_webhook_manager(storage_path: str = None) -> WebhookManager:
    """Factory function"""
    return WebhookManager(storage_path)
