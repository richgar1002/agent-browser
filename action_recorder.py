"""
Action Recorder & Playback
Record browser actions and replay them
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of browser actions"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    WAIT = "wait"
    SCROLL = "scroll"
    HOVER = "hover"
    EXECUTE = "execute"
    SCREENSHOT = "screenshot"


@dataclass
class Action:
    """A single browser action"""
    type: ActionType
    selector: str = None
    value: Any = None
    delay: float = 0  # Delay after action (seconds)
    description: str = ""
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type.value,
            'selector': self.selector,
            'value': self.value,
            'delay': self.delay,
            'description': self.description,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Action':
        return cls(
            type=ActionType(data['type']),
            selector=data.get('selector'),
            value=data.get('value'),
            delay=data.get('delay', 0),
            description=data.get('description', ''),
            timestamp=data.get('timestamp')
        )


@dataclass
class Workflow:
    """A recorded workflow"""
    id: str
    name: str
    description: str = ""
    actions: List[Action] = field(default_factory=list)
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'actions': [a.to_dict() for a in self.actions],
            'created_at': self.created_at,
            'updated_at': self.updated_at or datetime.now().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Workflow':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            actions=[Action.from_dict(a) for a in data.get('actions', [])],
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


class ActionRecorder:
    """
    Record and playback browser workflows
    """
    
    WORKFLOWS_FILE = "workflows.json"
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self.is_recording = False
        self.current_workflow: Workflow = None
        self._load_workflows()
    
    def _load_workflows(self):
        """Load workflows from storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WORKFLOWS_FILE}"
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for wf_data in data.get('workflows', []):
                self.workflows[wf_data['id']] = Workflow.from_dict(wf_data)
                
        except FileNotFoundError:
            logger.info("No workflows file found")
        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
    
    def _save_workflows(self):
        """Save workflows to storage"""
        if not self.storage_path:
            return
        
        try:
            file_path = f"{self.storage_path}/{self.WORKFLOWS_FILE}"
            data = {
                'workflows': [wf.to_dict() for wf in self.workflows.values()]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving workflows: {e}")
    
    # --- Recording ---
    
    def start_recording(self, name: str, description: str = "") -> str:
        """Start recording a new workflow"""
        if self.is_recording:
            logger.warning("Already recording")
            return None
        
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description
        )
        
        self.is_recording = True
        logger.info(f"Started recording: {name}")
        
        return workflow_id
    
    def record_action(
        self,
        action_type: ActionType,
        selector: str = None,
        value: Any = None,
        description: str = "",
        delay: float = 0
    ):
        """Record an action"""
        if not self.is_recording or not self.current_workflow:
            logger.warning("Not recording")
            return
        
        action = Action(
            type=action_type,
            selector=selector,
            value=value,
            description=description,
            delay=delay
        )
        
        self.current_workflow.actions.append(action)
        logger.debug(f"Recorded: {action_type.value} - {description}")
    
    def stop_recording(self) -> Optional[Workflow]:
        """Stop recording and save workflow"""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        
        if self.current_workflow:
            self.workflows[self.current_workflow.id] = self.current_workflow
            self._save_workflows()
            
            logger.info(f"Saved workflow: {self.current_workflow.name} ({len(self.current_workflow.actions)} actions)")
            
            workflow = self.current_workflow
            self.current_workflow = None
            return workflow
        
        return None
    
    def cancel_recording(self):
        """Cancel current recording without saving"""
        self.is_recording = False
        self.current_workflow = None
        logger.info("Recording cancelled")
    
    # --- Playback ---
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """List all workflows"""
        return list(self.workflows.values())
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            self._save_workflows()
            return True
        return False
    
    # --- Import/Export ---
    
    def export_workflow(self, workflow_id: str) -> str:
        """Export workflow as JSON"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return ""
        
        return json.dumps(workflow.to_dict(), indent=2)
    
    def import_workflow(self, json_str: str) -> bool:
        """Import workflow from JSON"""
        try:
            data = json.loads(json_str)
            workflow = Workflow.from_dict(data)
            
            self.workflows[workflow.id] = workflow
            self._save_workflows()
            
            logger.info(f"Imported workflow: {workflow.name}")
            return True
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
    
    # --- Convenience methods ---
    
    def record_navigate(self, url: str):
        """Record a navigation action"""
        self.record_action(
            ActionType.NAVIGATE,
            value=url,
            description=f"Navigate to {url}"
        )
    
    def record_click(self, selector: str, description: str = ""):
        """Record a click action"""
        self.record_action(
            ActionType.CLICK,
            selector=selector,
            description=description or f"Click {selector}"
        )
    
    def record_type(self, selector: str, value: str, description: str = ""):
        """Record a type action"""
        self.record_action(
            ActionType.TYPE,
            selector=selector,
            value=value,
            description=description or f"Type in {selector}"
        )
    
    def record_wait(self, seconds: float, description: str = ""):
        """Record a wait action"""
        self.record_action(
            ActionType.WAIT,
            value=seconds,
            delay=seconds,
            description=description or f"Wait {seconds}s"
        )


def create_action_recorder(storage_path: str = None) -> ActionRecorder:
    """Factory function"""
    return ActionRecorder(storage_path)
