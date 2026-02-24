"""
SeleniumBase + Playwright stealth approach for Axiom.trade authentication.

This method uses SeleniumBase's undetectable Chrome browser and connects
Playwright to it via CDP (Chrome DevTools Protocol).

Benefits:
- SeleniumBase's stealth features bypass Cloudflare
- Playwright's familiar API for automation
- Automatic captcha solving capabilities
- WSL-compatible (auto-detects Playwright's Chromium)
"""

from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
import json
import os
import glob


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


def capture_axiom_auth_stealth():
    """
    Capture authentication cookies from axiom.trade using SeleniumBase stealth mode.
    
    How it works:
    1. SeleniumBase launches undetectable Chrome
    2. Playwright connects to it via CDP
    3. You login manually
    4. Cookies are saved for reuse
    """
    
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
    
    # Connect Playwright to the SeleniumBase browser
    # Note: We don't use context manager cleanup to avoid conflicts with SeleniumBase
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(endpoint_url)
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("📍 Navigating to axiom.trade...")
        page.goto("https://axiom.trade/")
        
        print("\n" + "="*60)
        print("⚠️  MANUAL LOGIN REQUIRED")
        print("="*60)
        print("The browser window is now open and STEALTH-ENABLED.")
        print("Cloudflare should NOT detect you as a bot.")
        print("\nPlease:")
        print("  1. Complete any Turnstile/captcha challenges")
        print("  2. Log in with your credentials")
        print("  3. Wait for the dashboard to load")
        print("\nPress ENTER here when you're logged in...")
        print("="*60 + "\n")
        
        input()  # Wait for user to login
        
        # Give page time to settle
        sb.sleep(2)
        
        # Capture cookies
        print("\n📦 Capturing cookies...")
        cookies = context.cookies()
        
        print(f"✅ Captured {len(cookies)} cookies:")
        for cookie in cookies:
            value_preview = cookie['value'][:30] + "..." if len(cookie['value']) > 30 else cookie['value']
            print(f"  - {cookie['name']}: {value_preview}")
        
        # Save to Playwright-compatible format
        auth_file = "playwright_stealth_browser/.auth/axiom_auth_sb.json"
        os.makedirs(os.path.dirname(auth_file), exist_ok=True)
        
        storage_state = context.storage_state(path=auth_file)
        print(f"\n💾 Authentication saved to: {auth_file}")
        
        # Verify critical cookies
        cookie_names = [cookie['name'] for cookie in cookies]
        auth_cookies = ['auth-access-token', 'auth-refresh-token', 'cf_clearance', '__cf_bm']
        
        print("\n🔍 Cookie Verification:")
        all_present = True
        for auth_cookie in auth_cookies:
            if auth_cookie in cookie_names:
                print(f"  ✅ {auth_cookie}")
            else:
                print(f"  ❌ {auth_cookie} - MISSING")
                all_present = False
        
        if all_present:
            print("\n✅ All critical cookies captured successfully!")
        else:
            print("\n⚠️  Some cookies are missing - you may not be fully logged in")
        
        print("\n🎉 Done! You can now use this auth with regular Playwright tests.")
        print("Browser will close in 3 seconds...")
        sb.sleep(3)
    finally:
        # Cleanup Playwright (browser will be closed by SeleniumBase)
        p.stop()


def test_with_saved_auth():
    """
    Test using previously saved auth state with SeleniumBase stealth.
    """
    
    auth_file = "playwright_stealth_browser/.auth/axiom_auth_sb.json"
    
    if not os.path.exists(auth_file):
        print(f"❌ Auth file not found: {auth_file}")
        print("Run capture_axiom_auth_stealth() first!")
        return
    
    print("🚀 Launching SeleniumBase stealth Chrome...")
    
    sb = sb_cdp.Chrome(
        locale="en",
        headed=True,
        browser_executable_path=CHROME_BINARY
    )
    endpoint_url = sb.get_endpoint_url()
    
    # Don't use context manager to avoid browser close conflicts
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(endpoint_url)
        
        # Create new context with saved auth
        print(f"📂 Loading auth from: {auth_file}")
        context = browser.new_context(storage_state=auth_file)
        page = context.new_page()
        
        print("📍 Navigating to axiom.trade (should be logged in)...")
        # Use 'domcontentloaded' instead of 'networkidle' to avoid timeouts
        page.goto("https://axiom.trade/", wait_until="domcontentloaded")
        
        # Verify cookies
        cookies = context.cookies()
        cookie_names = [cookie['name'] for cookie in cookies]
        
        if 'auth-access-token' in cookie_names:
            print("✅ Authenticated session loaded!")
            print(f"📊 Total cookies: {len(cookies)}")
        else:
            print("❌ Auth cookies not found - session may have expired")
        
        print("\n⏸️  Keeping browser open for 10 seconds...")
        print("Check if you're logged in!")
        sb.sleep(10)
    finally:
        p.stop()


def extract_cookies_for_websocket():
    """
    Extract cookies in the format needed for your WebSocket connection.
    """
    
    auth_file = "playwright_stealth_browser/.auth/axiom_auth_sb.json"
    
    if not os.path.exists(auth_file):
        print(f"❌ Auth file not found: {auth_file}")
        return None
    
    with open(auth_file, 'r') as f:
        storage_state = json.load(f)
    
    cookies = storage_state.get('cookies', [])
    
    # Build cookie header string
    cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    
    # Extract specific tokens
    auth_tokens = {}
    for cookie in cookies:
        if cookie['name'] in ['auth-access-token', 'auth-refresh-token', 'cf_clearance', '__cf_bm']:
            auth_tokens[cookie['name']] = cookie['value']
    
    print("🍪 Extracted Cookies for WebSocket:\n")
    print(f"Cookie Header String (use this in headers):")
    print(f'"{cookie_header}"\n')
    
    print("Individual tokens:")
    for name, value in auth_tokens.items():
        print(f"{name}: {value[:50]}...")
    
    return {
        'cookie_header': cookie_header,
        'tokens': auth_tokens
    }


if __name__ == "__main__":
    print("=" * 60)
    print("SeleniumBase + Playwright Stealth Auth for Axiom.trade")
    print("=" * 60)
    print("\nOptions:")
    print("1. Capture auth (first time - manual login)")
    print("2. Test with saved auth")
    print("3. Extract cookies for WebSocket")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        capture_axiom_auth_stealth()
    elif choice == "2":
        test_with_saved_auth()
    elif choice == "3":
        extract_cookies_for_websocket()
    else:
        print("Invalid choice!")
