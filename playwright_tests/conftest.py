import os
import glob
import pytest
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp

# Auto-detect Chrome/Chromium binary for WSL compatibility
def get_chrome_binary():
    """Find Chrome or Playwright's Chromium binary."""
    # Try Playwright's Chromium first (for WSL)
    playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
    chrome_paths = glob.glob(f"{playwright_cache}/chromium-*/chrome-linux*/chrome")
    
    if chrome_paths:
        return chrome_paths[0]
    
    # Let SeleniumBase find Chrome itself (if installed)
    return None


CHROME_BINARY = get_chrome_binary()

@pytest.fixture(scope="session")
def browser():
    """Create a browser instance for the entire test session."""
    
    print("🚀 Launching SeleniumBase stealth Chrome browser...")
    if CHROME_BINARY:
        print(f"📍 Using Chromium: {CHROME_BINARY}")
    
    # Launch SeleniumBase Chrome in CDP mode (undetectable)
    sb = sb_cdp.Chrome(
        locale="en",
        headed=True,
        browser_executable_path=CHROME_BINARY
    )
    endpoint_url = sb.get_endpoint_url()
    
    print(f"🔗 CDP Endpoint: {endpoint_url}")
    print("✅ Browser launched with stealth settings\n")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(endpoint_url)
        yield browser
        browser.close()


@pytest.fixture
def context(browser):
    """Create a new browser context for each test."""
    # Require saved auth for tests - fail if not found
    auth_file = "playwright_stealth_browser/.auth/axiom_auth_sb.json"
    
    if not os.path.exists(auth_file):
        pytest.fail(
            f"❌ Authentication file not found: {auth_file}\n"
            f"Please run the auth capture script first:\n"
            f"  python axiom_login_test.py\n"
            f"Then choose option 1 to capture authentication."
        )
    
    # Load saved authentication state
    print(f"📂 Loading auth from: {auth_file}")
    context = browser.new_context(storage_state=auth_file)
    print(f"✅ Authentication loaded successfully")
    
    yield context
    context.close()


@pytest.fixture
def page(context):
    """Create a new page for each test."""
    page = context.new_page()
    yield page
    page.close()
