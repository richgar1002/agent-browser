"""
Session Manager - Persistent browser sessions
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import config

class SessionManager:
    """Manage browser sessions"""
    
    def __init__(self, sessions_dir: Path = None):
        self.sessions_dir = sessions_dir or config.SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_path(self, session_name: str) -> Path:
        """Get path for session file"""
        # Sanitize name
        safe_name = "".join(c for c in session_name if c.isalnum() or c in "-_")
        return self.sessions_dir / f"{safe_name}.json"
    
    def save_session(self, session_name: str, session_data: Dict):
        """Save session data"""
        path = self._get_session_path(session_name)
        
        # Add metadata
        session_data["name"] = session_name
        session_data["saved_at"] = datetime.now().isoformat()
        
        with open(path, "w") as f:
            json.dump(session_data, f, indent=2)
    
    def load_session(self, session_name: str) -> Optional[Dict]:
        """Load session data"""
        path = self._get_session_path(session_name)
        
        if not path.exists():
            return None
        
        try:
            with open(path, "r") as f:
                session_data = json.load(f)
            
            # Check if expired
            saved_at = datetime.fromisoformat(session_data.get("saved_at", "2000-01-01"))
            expiry = timedelta(hours=config.SESSION_EXPIRY_HOURS)
            
            if datetime.now() - saved_at > expiry:
                # Session expired, delete it
                path.unlink()
                return None
            
            return session_data
            
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
    
    def delete_session(self, session_name: str):
        """Delete a session"""
        path = self._get_session_path(session_name)
        if path.exists():
            path.unlink()
    
    def list_sessions(self) -> Dict:
        """List all saved sessions"""
        sessions = {}
        
        for path in self.sessions_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                
                sessions[path.stem] = {
                    "saved_at": data.get("saved_at"),
                    "has_cookies": bool(data.get("cookies")),
                    "has_storage": bool(data.get("local_storage"))
                }
            except (json.JSONDecodeError, IOError, KeyError):
                pass
        
        return sessions
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        removed = 0
        
        for path in self.sessions_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                
                saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
                expiry = timedelta(hours=config.SESSION_EXPIRY_HOURS)
                
                if datetime.now() - saved_at > expiry:
                    path.unlink()
                    removed += 1
            except (json.JSONDecodeError, IOError, KeyError):
                pass
        
        return removed
    
    def export_session(self, session_name: str, export_path: Path) -> bool:
        """Export session to file"""
        session_data = self.load_session(session_name)
        
        if not session_data:
            return False
        
        with open(export_path, "w") as f:
            json.dump(session_data, f, indent=2)
        
        return True
    
    def import_session(self, import_path: Path, session_name: str = None) -> bool:
        """Import session from file"""
        if not import_path.exists():
            return False
        
        try:
            with open(import_path, "r") as f:
                session_data = json.load(f)
            
            # Set name if not provided
            if session_name:
                session_data["name"] = session_name
            
            # Save
            name = session_data.get("name", import_path.stem)
            self.save_session(name, session_data)
            
            return True
        except Exception as e:
            print(f"Error importing session: {e}")
            return False
