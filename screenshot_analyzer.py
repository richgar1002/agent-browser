"""
Screenshot Analysis
OCR, visual element detection, and AI-powered page understanding
"""
import base64
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScreenAnalysis:
    """Result of screenshot analysis"""
    text: str = ""
    elements: List[Dict] = None
    buttons: List[str] = None
    links: List[str] = None
    inputs: List[str] = None
    images: List[str] = None
    summary: str = ""
    error: str = None
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []


class ScreenshotAnalyzer:
    """
    Analyze screenshots for text, elements, and structure
    """
    
    def __init__(self):
        self.ollama_available = False
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is available"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = response.status_code == 200
            if self.ollama_available:
                logger.info("Ollama is available for analysis")
        except (requests.RequestException, ConnectionError, TimeoutError):
            logger.info("Ollama not available, using basic OCR")
    
    def analyze(self, image_path: str = None, image_data: str = None) -> ScreenAnalysis:
        """
        Analyze a screenshot
        
        Args:
            image_path: Path to image file
            image_data: Base64 encoded image data
            
        Returns:
            ScreenAnalysis with extracted information
        """
        if not image_path and not image_data:
            return ScreenAnalysis(error="No image provided")
        
        try:
            # Try OCR first
            text = self._extract_text(image_path or image_data)
            
            # Get structure
            elements = self._detect_elements(image_path or image_data)
            
            # Categorize elements
            buttons = [e['text'] for e in elements if e.get('type') == 'button']
            links = [e['href'] for e in elements if e.get('href')]
            inputs = [e['id'] for e in elements if e.get('type') == 'input']
            
            # Generate summary with AI if available
            summary = ""
            if self.ollama_available:
                summary = self._generate_summary(text, elements)
            
            return ScreenAnalysis(
                text=text,
                elements=elements,
                buttons=buttons,
                links=links,
                inputs=inputs,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return ScreenAnalysis(error=str(e))
    
    def _extract_text(self, image_source: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Try pytesseract first
            import pytesseract
            from PIL import Image
            
            if image_source.startswith('/'):
                img = Image.open(image_source)
            else:
                # Base64
                import io
                img = Image.open(io.BytesIO(base64.b64decode(image_source)))
            
            text = pytesseract.image_to_string(img)
            return text.strip()
            
        except ImportError:
            logger.info("pytesseract not available")
            return "[OCR not available - install pytesseract]"
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def _detect_elements(self, image_source: str) -> List[Dict]:
        """Detect visual elements in screenshot"""
        # Basic implementation - could use computer vision
        # For now, returns empty list
        # In production, would use something like:
        # - OpenCV for edge detection
        # - ML model for element classification
        
        elements = []
        
        # This is a placeholder for actual CV implementation
        # Would detect: buttons, inputs, links, images, text blocks
        
        return elements
    
    def _generate_summary(self, text: str, elements: List[Dict]) -> str:
        """Generate AI summary of the page"""
        try:
            import requests
            
            prompt = f"""Analyze this webpage screenshot/text and provide a brief summary:
            
Text content: {text[:500]}
Elements found: {len(elements)}

Provide a 1-2 sentence summary of what this page is about."""
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
        
        return ""
    
    def compare_screenshots(
        self, 
        before: str, 
        after: str
    ) -> Dict:
        """
        Compare two screenshots to detect changes
        
        Args:
            before: Path or base64 of before image
            after: Path or base64 of after image
            
        Returns:
            Dict with change analysis
        """
        try:
            # Get text from both
            text_before = self._extract_text(before)
            text_after = self._extract_text(after)
            
            # Simple text diff
            before_lines = set(text_before.split('\n'))
            after_lines = set(text_after.split('\n'))
            
            added = after_lines - before_lines
            removed = before_lines - after_lines
            
            return {
                'changed': len(added) > 0 or len(removed) > 0,
                'added': list(added)[:10],
                'removed': list(removed)[:10],
                'similarity': len(before_lines & after_lines) / max(len(before_lines | after_lines), 1)
            }
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {'error': str(e)}
    
    def find_element_by_text(
        self, 
        screenshot: str, 
        text: str
    ) -> Optional[Dict]:
        """
        Find the approximate location of text in screenshot
        Returns bounding box if found
        """
        try:
            import pytesseract
            from PIL import Image
            import numpy as np
            
            # Load image
            if screenshot.startswith('/'):
                img = Image.open(screenshot)
            else:
                import io
                img = Image.open(io.BytesIO(base64.b64decode(screenshot)))
            
            # Get data
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Find text
            texts = data['text']
            for i, t in enumerate(texts):
                if text.lower() in t.lower():
                    return {
                        'text': t,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'confidence': data['conf'][i]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Element search failed: {e}")
            return None


def create_screenshot_analyzer() -> ScreenshotAnalyzer:
    """Factory function"""
    return ScreenshotAnalyzer()
