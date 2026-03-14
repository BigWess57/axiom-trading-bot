"""
Browser launch and auth loading for stealth browser automation.

Handles:
- Auto-detecting the Chromium binary (WSL-compatible)
- Launching SeleniumBase stealth Chrome via CDP
- Loading saved auth state from .auth/axiom_auth_sb.json
- Fail-fast if auth is missing or browser fails to connect
"""
import os
import glob
import logging
from playwright.sync_api import sync_playwright, Browser, Page

from seleniumbase import sb_cdp

from .endpoints import Endpoints

logger = logging.getLogger(__name__)

AUTH_FILE = "playwright_stealth_browser/.auth/axiom_auth_sb.json"


import sys

def get_chrome_binary() -> str | None:
    """Auto-detect Playwright's Chromium binary (cross-platform)."""
    if sys.platform == "win32":
        playwright_cache = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
        paths = glob.glob(f"{playwright_cache}\\chromium-*\\chrome-win*\\chrome.exe")
    else:
        playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
        paths = glob.glob(f"{playwright_cache}/chromium-*/chrome-linux*/chrome")
        
    return paths[0] if paths else None


def launch_stealth_browser(
    auth_file: str = AUTH_FILE,
    pre_navigate=None,
) -> tuple[object, Browser, Page]:
    """
    Launch a stealth browser with saved auth and navigate to axiom.trade/pulse.

    Args:
        auth_file: Path to the saved Playwright storage_state JSON.
        pre_navigate: Optional callable(page) invoked BEFORE page.goto().
                      Use this to attach WebSocket interceptors so no
                      connections are missed during the initial page load.

    Returns:
        (sb, playwright, browser, page) — caller is responsible for cleanup.

    Raises:
        RuntimeError: if auth file is missing or browser fails to launch.
    """
    if not os.path.exists(auth_file):
        raise RuntimeError(
            f"Auth file not found: {auth_file}\n"
            "Run the auth capture script first in:\n"
            "  python playwright_tests/axiom_login_test.py"
        )

    chrome_binary = get_chrome_binary()
    logger.info("Launching stealth Chrome%s", f" ({chrome_binary})" if chrome_binary else "")

    try:
        sb = sb_cdp.Chrome(
            locale="en",
            headed=False,
            browser_executable_path=chrome_binary,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to launch SeleniumBase Chrome: {e}") from e

    endpoint_url = sb.get_endpoint_url()
    logger.info("CDP endpoint: %s", endpoint_url)

    # Connect Playwright over CDP so we can use page.on("websocket")
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(endpoint_url)
    except Exception as e:
        p.stop()
        raise RuntimeError(f"Failed to connect Playwright over CDP: {e}") from e

    logger.info("Loading auth from: %s", auth_file)
    context = browser.new_context(storage_state=auth_file)
    page = context.new_page()

    # CRITICAL: attach interceptors BEFORE goto() so WebSocket events
    # that fire during page load are not missed.
    if pre_navigate:
        pre_navigate(page)

    logger.info("Navigating to axiom.trade/pulse...")
    page.goto(Endpoints.PULSE, wait_until="domcontentloaded")
    logger.info("Page loaded: %s", page.url)

    return sb, p, browser, page
