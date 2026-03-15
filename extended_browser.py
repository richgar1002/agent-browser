"""
Extended Browser Capabilities
- Multi-tab support
- File upload/download
- Proxy rotation
- Advanced JS injection
"""
import asyncio
import os
import shutil
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === MULTI-TAB SUPPORT ===

@dataclass
class Tab:
    """Browser tab"""
    id: str
    page: Any  # Playwright page
    url: str = ""
    title: str = ""
    active: bool = False


class TabManager:
    """
    Manage multiple browser tabs
    """
    
    def __init__(self, context):
        self.context = context
        self.tabs: Dict[str, Tab] = {}
        self.active_tab_id: Optional[str] = None
        self._tab_counter = 0
    
    async def create_tab(self, url: str = None) -> Tab:
        """Create a new tab"""
        self._tab_counter += 1
        tab_id = f"tab_{self._tab_counter}"
        
        # Create new page
        page = await self.context.new_page()
        
        # Navigate if URL provided
        if url:
            await page.goto(url)
        
        tab = Tab(
            id=tab_id,
            page=page,
            url=url or "",
            title=await page.title() if page else "",
            active=True
        )
        
        self.tabs[tab_id] = tab
        
        # Deactivate other tabs
        for other_id, other_tab in self.tabs.items():
            if other_id != tab_id:
                other_tab.active = False
        
        self.active_tab_id = tab_id
        logger.info(f"Created tab: {tab_id}")
        
        return tab
    
    async def close_tab(self, tab_id: str) -> bool:
        """Close a tab"""
        if tab_id not in self.tabs:
            return False
        
        tab = self.tabs[tab_id]
        await tab.page.close()
        del self.tabs[tab_id]
        
        # Activate another tab if this was active
        if self.active_tab_id == tab_id:
            if self.tabs:
                self.active_tab_id = list(self.tabs.keys())[0]
                self.tabs[self.active_tab_id].active = True
            else:
                self.active_tab_id = None
        
        logger.info(f"Closed tab: {tab_id}")
        return True
    
    async def switch_tab(self, tab_id: str) -> bool:
        """Switch to a tab"""
        if tab_id not in self.tabs:
            return False
        
        # Deactivate current
        if self.active_tab_id and self.active_tab_id in self.tabs:
            self.tabs[self.active_tab_id].active = False
        
        # Activate new
        self.active_tab_id = tab_id
        self.tabs[tab_id].active = True
        
        # Bring to front
        await self.tabs[tab_id].page.bring_to_front()
        
        logger.info(f"Switched to tab: {tab_id}")
        return True
    
    def get_tab(self, tab_id: str) -> Optional[Tab]:
        """Get a tab"""
        return self.tabs.get(tab_id)
    
    def get_active_tab(self) -> Optional[Tab]:
        """Get active tab"""
        if self.active_tab_id:
            return self.tabs.get(self.active_tab_id)
        return None
    
    def list_tabs(self) -> List[Dict]:
        """List all tabs"""
        return [
            {
                'id': tab.id,
                'url': tab.url,
                'title': tab.title,
                'active': tab.active
            }
            for tab in self.tabs.values()
        ]
    
    async def close_all(self):
        """Close all tabs"""
        for tab in list(self.tabs.values()):
            await tab.page.close()
        self.tabs.clear()
        self.active_tab_id = None


# === FILE OPERATIONS ===

class FileHandler:
    """
    Handle file uploads and downloads
    """
    
    def __init__(self, download_dir: str = None):
        self.download_dir = download_dir or "/tmp/browser_downloads"
        os.makedirs(self.download_dir, exist_ok=True)
    
    async def upload_file(self, page, selector: str, file_path: str) -> bool:
        """
        Upload a file to input element
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Set input files
            await page.set_input_files(selector, file_path)
            logger.info(f"Uploaded file to {selector}: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    async def download_wait(
        self,
        page,
        trigger_fn,
        filename_pattern: str = None,
        timeout: int = 30000
    ) -> Optional[str]:
        """
        Wait for download to complete
        trigger_fn: function that triggers the download
        """
        download = None
        
        # Start download listener
        async with page.expect_download(timeout=timeout) as download_info:
            await trigger_fn()
        
        try:
            download = await download_info.value
            
            # Generate filename
            suggested = download.suggested_filename
            if filename_pattern:
                final_name = filename_pattern.replace("*", suggested)
            else:
                final_name = suggested
            
            # Save to download directory
            save_path = os.path.join(self.download_dir, final_name)
            await download.save_as(save_path)
            
            logger.info(f"Downloaded: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    async def download_click(
        self,
        page,
        selector: str,
        filename_pattern: str = None
    ) -> Optional[str]:
        """
        Click element and wait for download
        """
        async def trigger():
            await page.click(selector)
        
        return await self.download_wait(page, trigger, filename_pattern)
    
    def list_downloads(self) -> List[Dict]:
        """List downloaded files"""
        files = []
        
        for filename in os.listdir(self.download_dir):
            filepath = os.path.join(self.download_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def delete_download(self, filename: str) -> bool:
        """Delete a downloaded file"""
        filepath = os.path.join(self.download_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def clear_downloads(self):
        """Clear all downloads"""
        for filename in os.listdir(self.download_dir):
            filepath = os.path.join(self.download_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)


# === PROXY ROTATION ===

class ProxyManager:
    """
    Manage proxy rotation
    """
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.current_index = 0
        self.failed_proxies: set = set()
    
    def add_proxy(
        self,
        host: str,
        port: int,
        username: str = None,
        password: str = None,
        name: str = None
    ):
        """Add a proxy"""
        proxy = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'name': name or f"{host}:{port}",
            'used': 0,
            'failed': 0
        }
        
        self.proxies.append(proxy)
        logger.info(f"Added proxy: {proxy['name']}")
    
    def load_from_file(self, filepath: str):
        """Load proxies from file (format: host:port:user:pass)"""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 2:
                        host, port = parts[0], int(parts[1])
                        user = parts[2] if len(parts) > 2 else None
                        password = parts[3] if len(parts) > 3 else None
                        self.add_proxy(host, port, user, password)
                        
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
    
    def get_next_proxy(self) -> Optional[Dict]:
        """Get next proxy (round-robin)"""
        if not self.proxies:
            return None
        
        # Find next working proxy
        attempts = 0
        start_index = self.current_index
        
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            # Skip failed proxies
            if proxy['name'] in self.failed_proxies:
                attempts += 1
                continue
            
            proxy['used'] += 1
            return proxy
        
        return None
    
    def mark_failed(self, proxy_name: str):
        """Mark proxy as failed"""
        for proxy in self.proxies:
            if proxy['name'] == proxy_name:
                proxy['failed'] += 1
                self.failed_proxies.add(proxy_name)
                logger.warning(f"Proxy failed: {proxy_name}")
                break
    
    def mark_success(self, proxy_name: str):
        """Mark proxy as successful"""
        if proxy_name in self.failed_proxies:
            self.failed_proxies.remove(proxy_name)
            logger.info(f"Proxy restored: {proxy_name}")
    
    def get_stats(self) -> Dict:
        """Get proxy stats"""
        return {
            'total': len(self.proxies),
            'available': len([p for p in self.proxies if p['name'] not in self.failed_proxies]),
            'failed': len(self.failed_proxies),
            'proxies': [
                {
                    'name': p['name'],
                    'used': p['used'],
                    'failed': p['failed'],
                    'status': 'failed' if p['name'] in self.failed_proxies else 'active'
                }
                for p in self.proxies
            ]
        }
    
    def get_playwright_proxy(self, proxy: Dict = None) -> Optional[Dict]:
        """Get Playwright proxy config"""
        if not proxy:
            proxy = self.get_next_proxy()
        
        if not proxy:
            return None
        
        config = {
            'server': f"http://{proxy['host']}:{proxy['port']}"
        }
        
        if proxy.get('username'):
            config['username'] = proxy['username']
            config['password'] = proxy['password']
        
        return config


# === JAVASCRIPT INJECTION ===

class JSInjector:
    """
    Advanced JavaScript injection
    """
    
    # Common useful scripts
    SCRIPTS = {
        'scroll_to_bottom': """
            window.scrollTo(0, document.body.scrollHeight);
        """,
        'scroll_to_top': """
            window.scrollTo(0, 0);
        """,
        'get_all_links': """
            Array.from(document.querySelectorAll('a')).map(a => ({
                href: a.href,
                text: a.innerText.trim(),
                title: a.title
            }));
        """,
        'get_all_images': """
            Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.width,
                height: img.height
            }));
        """,
        'get_meta_tags': """
            Array.from(document.querySelectorAll('meta')).reduce((acc, meta) => {
                if (meta.name) acc[meta.name] = meta.content;
                if (meta.property) acc[meta.property] = meta.content;
                return acc;
            }, {});
        """,
        'get_forms': """
            Array.from(document.querySelectorAll('form')).map(form => ({
                action: form.action,
                method: form.method,
                inputs: Array.from(form.elements).map(el => ({
                    name: el.name,
                    type: el.type,
                    required: el.required
                }))
            }));
        """,
        'remove_ads': """
            const selectors = ['.ad', '.ads', '.advertisement', '[class*="ad-"]', '[id*="ad-"]'];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
            true;
        """,
        'block_requests': """
            // Returns function to block requests
            (function() {
                const patterns = arguments;
                return function(url) {
                    return patterns.some(p => url.includes(p));
                };
            })
        """,
        'auto_scroll': """
            async function autoScroll() {
                const delay = arguments[0] || 100;
                const maxScroll = arguments[1] || 5;
                let scrolls = 0;
                
                while (scrolls < maxScroll) {
                    window.scrollBy(0, window.innerHeight);
                    await new Promise(r => setTimeout(r, delay));
                    scrolls++;
                }
            }
            autoScroll;
        """
    }
    
    def __init__(self, page):
        self.page = page
    
    async def run(self, script: str):
        """Run custom JavaScript"""
        return await self.page.evaluate(script)
    
    async def run_named(self, script_name: str, *args):
        """Run a named script"""
        if script_name not in self.SCRIPTS:
            raise ValueError(f"Unknown script: {script_name}")
        
        script = self.SCRIPTS[script_name]
        
        if args:
            # Inject arguments
            script = f"""
                (function() {{
                    {script}
                }})({', '.join(repr(a) for a in args)})
            """
        
        return await self.run(script)
    
    async def inject_jquery(self):
        """Inject jQuery"""
        jquery_cdn = """
            if (typeof jQuery == 'undefined') {
                var script = document.createElement('script');
                script.src = 'https://code.jquery.com/jquery-3.6.0.min.js';
                document.head.appendChild(script);
            }
        """
        await self.run(jquery_cdn)
    
    async def wait_for_element(self, selector: str, timeout: int = 10000):
        """Wait for element and return it"""
        script = f"""
            new Promise((resolve, reject) => {{
                if (document.querySelector('{selector}')) {{
                    resolve(document.querySelector('{selector}'));
                }}
                
                const observer = new MutationObserver(() => {{
                    if (document.querySelector('{selector}')) {{
                        observer.disconnect();
                        resolve(document.querySelector('{selector}'));
                    }}
                }});
                
                observer.observe(document.body, {{ childList: true, subtree: true }});
                
                setTimeout(() => {{
                    observer.disconnect();
                    reject(new Error('Element not found'));
                }}, {timeout});
            }})
        """
        return await self.run(script)


# === FACTORY ===

def create_file_handler(download_dir: str = None) -> FileHandler:
    """Create file handler"""
    return FileHandler(download_dir)


def create_proxy_manager() -> ProxyManager:
    """Create proxy manager"""
    return ProxyManager()
