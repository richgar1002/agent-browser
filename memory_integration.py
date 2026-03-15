"""
Browser Memory Integration
Connects Agent Browser to Memory Bridge (Supabase)
"""
import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ujfmhpbodscrzkwkynon.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


@dataclass
class PageSummary:
    """Summary of a web page"""
    url: str
    title: str
    content: str
    screenshot: Optional[str] = None
    tags: List[str] = None


class BrowserMemory:
    """
    Integration between Browser and Memory Bridge
    """
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or "browser"
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client"""
        try:
            from client_production import create_memory_client, ClientConfig
            
            config = ClientConfig(
                max_retries=3,
                retry_delay=2.0,
                verbose=False
            )
            
            self.client = create_memory_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY,
                user_id=self.user_id,
                config=config
            )
            logger.info("Browser memory client initialized")
            
        except Exception as e:
            logger.warning(f"Could not initialize memory client: {e}")
            self.client = None
    
    def save_page(self, page: PageSummary, auto_tag: bool = True) -> bool:
        """Save a page to memory"""
        if not self.client:
            logger.warning("Memory client not available")
            return False
        
        try:
            # Auto-generate tags if enabled
            tags = page.tags or []
            if auto_tag and not tags:
                tags = self._generate_tags(page)
            
            # Create memory
            self.client.create_memory(
                title=page.title,
                content=page.content[:10000],  # Limit content size
                tags=tags + ["browser", "saved"],
                source=f"browser:{page.url}"
            )
            
            logger.info(f"Saved page to memory: {page.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save page: {e}")
            return False
    
    def _generate_tags(self, page: PageSummary) -> List[str]:
        """Generate tags based on URL and title"""
        tags = []
        
        url_lower = page.url.lower()
        title_lower = page.title.lower()
        
        # Domain-based tags
        if "github" in url_lower:
            tags.append("github")
        elif "docs" in url_lower:
            tags.append("documentation")
        elif "amazon" in url_lower:
            tags.append("shopping")
        elif "news" in url_lower:
            tags.append("news")
        elif "youtube" in url_lower:
            tags.append("video")
        
        # Content-based tags
        if "api" in title_lower:
            tags.append("api")
        if "tutorial" in title_lower or "guide" in title_lower:
            tags.append("tutorial")
        if "error" in title_lower or "fix" in title_lower:
            tags.append("troubleshooting")
        
        return tags[:5]  # Max 5 tags
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memory while browsing"""
        if not self.client:
            return []
        
        try:
            results = self.client.search(query, limit=limit)
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_saved_pages(self, limit: int = 20) -> List[Dict]:
        """Get all saved browser pages"""
        if not self.client:
            return []
        
        try:
            memories = self.client.get_memories(limit=limit)
            # Filter to browser sources
            return [m for m in memories if m.get('source', '').startswith('browser:')]
            
        except Exception as e:
            logger.error(f"Failed to get pages: {e}")
            return []
    
    def delete_page(self, url: str) -> bool:
        """Delete a saved page"""
        if not self.client:
            return False
        
        try:
            memories = self.client.get_memories(limit=100)
            for memory in memories:
                if memory.get('source') == f"browser:{url}":
                    self.client.delete_memory(memory['id'])
                    logger.info(f"Deleted page: {url}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete page: {e}")
            return False
    
    def get_related(self, url: str, limit: int = 3) -> List[Dict]:
        """Get related pages from memory"""
        if not self.client:
            return []
        
        try:
            # Extract domain as search query
            domain = url.split('/')[2] if '/' in url else url
            return self.search_memory(domain, limit=limit)
            
        except Exception as e:
            logger.error(f"Failed to get related: {e}")
            return []


def create_browser_memory(user_id: str = None) -> BrowserMemory:
    """Factory function"""
    return BrowserMemory(user_id)
