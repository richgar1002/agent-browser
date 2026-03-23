"""
Agent Browser - Unified CLI
Complete CLI with all features
"""
import asyncio
import argparse
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

import config
try:
    from enhanced_browser import create_browser
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
        print(f"Navigated to: {args.url}")
        
        if args.screenshot:
            path = await browser.screenshot(args.screenshot)
            print(f"Screenshot saved: {path}")
        
        if args.save_memory:
            result = await browser.save_to_memory()
            print(f"Saved to memory: {result}")


async def cmd_screenshot(args):
    """Take screenshot"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        
        path = await browser.screenshot(args.path or "screenshot.png")
        print(f"Screenshot: {path}")


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
    """Fill form field"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        
        await browser.wait_for_selector(args.selector)
        await browser.fill(args.selector, args.value)
        print(f"Filled: {args.selector} = {args.value}")


async def cmd_evaluate(args):
    """Evaluate JavaScript"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        
        result = await browser.evaluate(args.js)
        print(result)


async def cmd_network(args):
    """Get network log"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await asyncio.sleep(2)  # Let requests happen
        
        log = browser.get_network_log()
        
        if args.json:
            print(json.dumps(log, indent=2))
        else:
            print(f"Requests: {len(log.get('requests', []))}")
            print(f"Responses: {len(log.get('responses', []))}")


async def cmd_memory_save(args):
    """Save page to memory"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        
        tags = args.tags.split(",") if args.tags else None
        result = await browser.save_to_memory(tags)
        print(f"Saved to memory: {result}")


async def cmd_memory_search(args):
    """Search memory"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        results = browser.search_memory(args.query, args.limit)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Found {len(results)} results:")
            for r in results:
                print(f"  - {r.get('title', 'Untitled')}")
                print(f"    {r.get('source', '')}")


async def cmd_analyze(args):
    """Analyze screenshot"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
        
        await browser.screenshot()
        result = await browser.analyze_screenshot()
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Text: {result.get('text', '')[:200]}...")
            print(f"Buttons: {result.get('buttons', [])}")
            print(f"Summary: {result.get('summary', '')}")


async def cmd_record_start(args):
    """Start action recording"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        browser.start_recording(args.name, args.description or "")
        print(f"Recording: {args.name}")
        print("Perform actions, then run: record stop")


async def cmd_record_stop(args):
    """Stop action recording"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        workflow = browser.stop_recording()
        if workflow:
            print(f"Saved workflow: {workflow.name} ({len(workflow.actions)} actions)")
        else:
            print("No recording in progress")


async def cmd_forms_list(args):
    """List forms"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        forms = browser.form_builder.list_forms()
        
        if args.json:
            print(json.dumps([f.to_dict() for f in forms], indent=2))
        else:
            print(f"Forms: {len(forms)}")
            for f in forms:
                print(f"  - {f.name} ({f.url_pattern})")


async def cmd_webhooks_list(args):
    """List webhooks"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        webhooks = browser.webhooks.list_webhooks()
        
        if args.json:
            print(json.dumps([w.to_dict() for w in webhooks], indent=2))
        else:
            print(f"Webhooks: {len(webhooks)}")
            for w in webhooks:
                status = "✅" if w.enabled else "❌"
                print(f"  {status} {w.name} - {w.trigger_type.value}: {w.trigger_value}")


async def cmd_session_list(args):
    """List sessions"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        sessions = browser.session_pool.list_sessions()
        
        if args.json:
            print(json.dumps(sessions, indent=2))
        else:
            print(f"Active sessions: {len(sessions)}")
            for s in sessions:
                print(f"  - {s['id']} ({s['state']})")


async def cmd_metrics(args):
    """Get network metrics"""
    _ensure_browser_available()
    async with create_browser(args.session) as browser:
        if args.url:
            await browser.go_to(args.url)
            await asyncio.sleep(2)
        
        metrics = browser.get_network_metrics()
        
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print(f"Total requests: {metrics.get('total_requests', 0)}")
            print(f"Total bytes: {metrics.get('total_bytes', 0)}")
            print(f"Domains: {list(metrics.get('by_domain', {}).keys())}")


async def main():
    parser = argparse.ArgumentParser(description="Agent Browser CLI")
    parser.add_argument("--session", default="default", help="Session name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Navigation
    nav_parser = subparsers.add_parser("goto", help="Navigate to URL")
    nav_parser.add_argument("url", help="URL to navigate")
    nav_parser.add_argument("--screenshot", help="Save screenshot")
    nav_parser.add_argument("--save-memory", action="store_true", help="Save to memory")
    
    # Screenshot
    ss_parser = subparsers.add_parser("screenshot", help="Take screenshot")
    ss_parser.add_argument("--url", help="URL to navigate first")
    ss_parser.add_argument("--path", help="Save path")
    
    # Click
    click_parser = subparsers.add_parser("click", help="Click element")
    click_parser.add_argument("selector", help="CSS selector")
    click_parser.add_argument("--url", help="URL to navigate first")
    
    # Fill
    fill_parser = subparsers.add_parser("fill", help="Fill input")
    fill_parser.add_argument("selector", help="CSS selector")
    fill_parser.add_argument("value", help="Value to fill")
    fill_parser.add_argument("--url", help="URL to navigate first")
    
    # Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate JS")
    eval_parser.add_argument("js", help="JavaScript code")
    eval_parser.add_argument("--url", help="URL to navigate first")
    
    # Network
    net_parser = subparsers.add_parser("network", help="Network log")
    net_parser.add_argument("--url", help="URL to navigate first")
    
    # Memory
    mem_parser = subparsers.add_parser("memory", help="Memory commands")
    mem_sub = mem_parser.add_subparsers(dest="mem_cmd")
    
    mem_save = mem_sub.add_parser("save", help="Save to memory")
    mem_save.add_argument("--url", help="URL to navigate")
    mem_save.add_argument("--tags", help="Comma-separated tags")
    
    mem_search = mem_sub.add_parser("search", help="Search memory")
    mem_search.add_argument("query", help="Search query")
    mem_search.add_argument("--limit", type=int, default=5)
    
    # Analyze
    ana_parser = subparsers.add_parser("analyze", help="Analyze screenshot")
    ana_parser.add_argument("--url", help="URL to navigate")
    
    # Record
    rec_parser = subparsers.add_parser("record", help="Action recording")
    rec_sub = rec_parser.add_subparsers(dest="rec_cmd")
    
    rec_start = rec_sub.add_parser("start", help="Start recording")
    rec_start.add_argument("name", help="Workflow name")
    rec_start.add_argument("--description", help="Description")
    
    rec_stop = rec_sub.add_parser("stop", help="Stop recording")
    
    # Forms
    forms_parser = subparsers.add_parser("forms", help="Form commands")
    
    # Webhooks
    wh_parser = subparsers.add_parser("webhooks", help="Webhook commands")
    
    # Session
    sess_parser = subparsers.add_parser("session", help="Session commands")
    sess_parser.add_argument("action", choices=["list"], help="Action")
    
    # Metrics
    met_parser = subparsers.add_parser("metrics", help="Network metrics")
    met_parser.add_argument("--url", help="URL to navigate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to handlers
    try:
        if args.command == "goto":
            await cmd_goto(args)
        elif args.command == "screenshot":
            await cmd_screenshot(args)
        elif args.command == "click":
            await cmd_click(args)
        elif args.command == "fill":
            await cmd_fill(args)
        elif args.command == "evaluate":
            await cmd_evaluate(args)
        elif args.command == "network":
            await cmd_network(args)
        elif args.command == "memory":
            if args.mem_cmd == "save":
                await cmd_memory_save(args)
            elif args.mem_cmd == "search":
                await cmd_memory_search(args)
        elif args.command == "analyze":
            await cmd_analyze(args)
        elif args.command == "record":
            if args.rec_cmd == "start":
                await cmd_record_start(args)
            elif args.rec_cmd == "stop":
                await cmd_record_stop(args)
        elif args.command == "forms":
            await cmd_forms_list(args)
        elif args.command == "webhooks":
            await cmd_webhooks_list(args)
        elif args.command == "session":
            await cmd_session_list(args)
        elif args.command == "metrics":
            await cmd_metrics(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
