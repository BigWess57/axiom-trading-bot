# SeleniumBase + Playwright Stealth Setup

## ✅ Installation Complete!

SeleniumBase is now installed. This gives you:
- **Undetectable Chrome** browser
- **Automatic captcha solving** (Turnstile, reCAPTCHA)
- **CDP mode** - Connect Playwright to SeleniumBase browser
- **All stealth patches** applied automatically

---

## 🚀 Quick Start - Capture Auth from Axiom.trade

### **Method 1: Use the Complete Script (RECOMMENDED)**

```bash
cd playwright_tests
python axiom_seleniumbase_stealth.py
# Choose option 1
```

This will:
1. ✅ Launch stealth Chrome (bypasses Cloudflare)
2. ✅ Navigate to axiom.trade
3. ✅ Let you login manually
4. ✅ Save all cookies to `.auth/axiom_auth_sb.json`
5. ✅ Extract cookies in WebSocket format

### **Method 2: Your Raw Test**

Your `raw_bing_cap_sync.py` now works (syntax fixed). To adapt it for axiom:

```bash
python raw_bing_cap_sync.py
```

---

## 📖 How This Works

### **The CDP Approach:**

```python
# 1. SeleniumBase launches undetectable Chrome
sb = sb_cdp.Chrome(
        locale="en",
        headed=True,
        browser_executable_path=CHROME_BINARY
    )
endpoint_url = sb.get_endpoint_url()

# 2. Playwright connects to it via Chrome DevTools Protocol
browser = p.chromium.connect_over_cdp(endpoint_url)

# 3. Use existing tab
context = browser.contexts[0]
page = context.pages[0]

# 4. Now you have Playwright API + SeleniumBase stealth!
page.goto("https://axiom.trade/")
```

**Why this is powerful:**
- ✅ SeleniumBase Chrome is **pre-patched** to be undetectable
- ✅ Bypasses `navigator.webdriver` detection
- ✅ Passes all bot detection tests
- ✅ You get Playwright's familiar API

---

## 🎯 Next Steps

### **Step 1: Capture Auth**

```bash
python axiom_seleniumbase_stealth.py
# Choose 1 - Manual login
```

Browser opens → Login manually → Cookies saved

### **Step 2: Extract Cookies for WebSocket**

```bash
python axiom_seleniumbase_stealth.py
# Choose 3 - Extract cookies
```

This gives you the cookie header string to use in your WebSocket connection!

### **Step 3: Update Your WebSocket Code**

The script will output something like:

```
Cookie Header String:
"auth-access-token=eyJhbG...; auth-refresh-token=eyJhbG...; cf_clearance=abc..."
```

Use this in your `manual_cookie_test.py` or `connection.py`:

```python
headers = {
    'Cookie': 'auth-access-token=eyJhbG...; cf_clearance=...',
    'User-Agent': '...',
    # ... other headers
}
```

---

## 🔍 Understanding the Files

| File | Purpose |
|------|---------|
| **`axiom_seleniumbase_stealth.py`** | Complete solution - 3 modes (capture, test, extract) |
| **`raw_bing_cap_sync.py`** | Your original test (fixed) - shows captcha solving |
| **`.auth/axiom_auth_sb.json`** | Saved cookies (created after first login) |

---

## 💡 Pro Tips

### **Automatic Captcha Solving**

SeleniumBase can solve captchas automatically:

```python
# If captcha appears
sb.solve_captcha()  # Handles Turnstile, reCAPTCHA, etc.
```

### **Reusing Cookies**

After capturing once, load cookies to skip login:

```python
context = browser.new_context(storage_state='.auth/axiom_auth_sb.json')
```

### **Checking for Cloudflare Block**

Visit this page to test detection:
```python
page.goto("https://www.bing.com/turing/captcha/challenge")
```

If it loads without captcha = undetected! ✅

---

## 🐛 Troubleshooting

### "selenium-stealth not found"
Already included in SeleniumBase - no extra install needed!

### Browser crashes or freezes
Add headless mode:
```python
sb = sb_cdp.Chrome(locale="en", headless=False)  # Set to True
```

### Cookies not saving
Make sure `.auth/` directory exists:
```bash
mkdir -p playwright_tests/.auth
```

---

## 🎉 You're Ready!

The stealth approach beats Cloudflare detection. Your next WebSocket connection with these cookies should work! 🚀
