"""
Original approach from SeleniumBase examples.
FIXED: Use uc_gui=True to show browser window on WSL/Linux!
"""

from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
import os
import glob

# Find Playwright's Chromium binary
playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
chrome_paths = glob.glob(f"{playwright_cache}/chromium-*/chrome-linux*/chrome")

if not chrome_paths:
    print("❌ Playwright Chromium not found!")
    print("Run: python -m playwright install chromium")
    exit(1)

chrome_binary = chrome_paths[0]
print(f"✅ Using Chromium: {chrome_binary}\n")

print("🚀 Launching browser with visible window...")

# Launch SeleniumBase browser 
# KEY FIX: Use uc_gui=True (this sets headed=True internally)
sb = sb_cdp.Chrome(
    locale="en",
    headed=True,  # This is the magic parameter for Linux/WSL!
    browser_executable_path=chrome_binary
)

# Get CDP endpoint
endpoint_url = sb.get_endpoint_url()
print(f"🔗 CDP Endpoint ready")

print("📍 Connecting Playwright...")

# Connect Playwright to the same browser
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(endpoint_url)
    context = browser.contexts[0]
    page = context.pages[0]
    
    print("✅ Playwright connected!")
    print("📍 Navigating to Bing captcha page...")
    
    page.goto("https://www.bing.com/turing/captcha/challenge")
    
    print("\n✅ Page loaded!")
    print("🔍 Browser window should NOW be visible!\n")
    print("Keeping window open for 10 seconds...")
    
    sb.sleep(10)
    
    print("\n✅ Done!")

print("Closing browser...")