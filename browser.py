"""
Agent Browser - Main Entry Point
Backward-compatible wrapper around enhanced_browser
"""
from enhanced_browser import EnhancedAgentBrowser, create_browser

# Alias for backward compatibility
AgentBrowser = EnhancedAgentBrowser

__all__ = ['AgentBrowser', 'create_browser', 'EnhancedAgentBrowser']
