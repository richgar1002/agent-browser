"""
Agent Browser - CLI
Command line interface for AI agents
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path

from session_manager import SessionManager

try:
    from browser import create_browser
    _BROWSER_IMPORT_ERROR = None
except Exception as exc:
    create_browser = None  # type: ignore[assignment]
    _BROWSER_IMPORT_ERROR = exc


def _ensure_browser_available():
    """Fail fast with dependency guidance."""
    if _BROWSER_IMPORT_ERROR:
        print(
            "Browser dependencies are missing. Install with:\n"
            "  pip install -r requirements.txt\n"
            "  playwright install chromium"
        )
        raise SystemExit(2) from _BROWSER_IMPORT_ERROR

async def cmd_goto(args):
    """Navigate to URL"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        await browser.go_to(args.url)
        print(f"Navigated to: {browser.current_url}")

async def cmd_screenshot(args):
    """Take screenshot"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await browser.wait_for_load_state()
        path = await browser.screenshot(args.path or None)
        print(f"Screenshot saved: {path}")

async def cmd_click(args):
    """Click element"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await browser.wait_for_selector(args.selector)
        await browser.click(args.selector)
        print(f"Clicked: {args.selector}")

async def cmd_fill(args):
    """Fill input"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await browser.wait_for_selector(args.selector)
        await browser.fill(args.selector, args.value)
        print(f"Filled {args.selector} with: {args.value}")

async def cmd_get_text(args):
    """Get text from element"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await browser.wait_for_selector(args.selector)
        text = await browser.get_text(args.selector)
        print(text)

async def cmd_evaluate(args):
    """Evaluate JavaScript"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        result = await browser.evaluate(args.javascript)
        print(json.dumps(result, indent=2))

async def cmd_session_list(args):
    """List sessions"""
    sm = SessionManager()
    sessions = sm.list_sessions()
    
    if not sessions:
        print("No sessions found")
        return
    
    print("Sessions:")
    for name, info in sessions.items():
        print(f"  {name}")
        print(f"    Saved: {info.get('saved_at', 'unknown')}")
        print(f"    Cookies: {'✓' if info.get('has_cookies') else '✗'}")

async def cmd_session_delete(args):
    """Delete session"""
    sm = SessionManager()
    sm.delete_session(args.name)
    print(f"Deleted session: {args.name}")

async def cmd_network(args):
    """Get network log"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await browser.wait_for_load_state()
        
        log = browser.get_network_log()
        
        if args.json:
            print(json.dumps(log, indent=2))
        else:
            print(f"Requests: {log['count']['requests']}")
            print(f"Responses: {log['count']['responses']}")
            print(f"API calls: {len(log.get('requests', []))}")

def main():
    parser = argparse.ArgumentParser(description="Agent Browser CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Session management
    session_parser = subparsers.add_parser("session", help="Session commands")
    session_sub = session_parser.add_subparsers(dest="session_command")
    
    list_parser = session_sub.add_parser("list", help="List sessions")
    list_parser.set_defaults(func=cmd_session_list)
    
    delete_parser = session_sub.add_parser("delete", help="Delete session")
    delete_parser.add_argument("name", help="Session name")
    delete_parser.set_defaults(func=cmd_session_delete)
    
    # Navigation
    goto_parser = subparsers.add_parser("goto", help="Navigate to URL")
    goto_parser.add_argument("url", help="URL to navigate to")
    goto_parser.add_argument("--session", default="default", help="Session name")
    goto_parser.set_defaults(func=cmd_goto)
    
    # Screenshot
    ss_parser = subparsers.add_parser("screenshot", help="Take screenshot")
    ss_parser.add_argument("--url", help="URL to navigate to first")
    ss_parser.add_argument("--path", help="Path to save screenshot")
    ss_parser.add_argument("--session", default="default", help="Session name")
    ss_parser.set_defaults(func=cmd_screenshot)
    
    # Click
    click_parser = subparsers.add_parser("click", help="Click element")
    click_parser.add_argument("selector", help="CSS selector")
    click_parser.add_argument("--url", help="URL to navigate to first")
    click_parser.add_argument("--session", default="default", help="Session name")
    click_parser.set_defaults(func=cmd_click)
    
    # Fill
    fill_parser = subparsers.add_parser("fill", help="Fill input")
    fill_parser.add_argument("selector", help="CSS selector")
    fill_parser.add_argument("value", help="Value to fill")
    fill_parser.add_argument("--url", help="URL to navigate to first")
    fill_parser.add_argument("--session", default="default", help="Session name")
    fill_parser.set_defaults(func=cmd_fill)
    
    # Get text
    text_parser = subparsers.add_parser("get-text", help="Get element text")
    text_parser.add_argument("selector", help="CSS selector")
    text_parser.add_argument("--url", help="URL to navigate to first")
    text_parser.add_argument("--session", default="default", help="Session name")
    text_parser.set_defaults(func=cmd_get_text)
    
    # Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate JavaScript")
    eval_parser.add_argument("javascript", help="JavaScript code")
    eval_parser.add_argument("--url", help="URL to navigate to first")
    eval_parser.add_argument("--session", default="default", help="Session name")
    eval_parser.set_defaults(func=cmd_evaluate)
    
    # Network
    net_parser = subparsers.add_parser("network", help="Network log")
    net_parser.add_argument("--url", help="URL to navigate to first")
    net_parser.add_argument("--json", action="store_true", help="JSON output")
    net_parser.add_argument("--session", default="default", help="Session name")
    net_parser.set_defaults(func=cmd_network)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run command
    if hasattr(args, 'func'):
        asyncio.run(args.func(args))
    elif args.command == "session":
        if not hasattr(args, 'session_command'):
            session_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
