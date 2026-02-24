# Playwright Tests for Axiom Trading Bot

## ⚠️ IMPORTANT: Cloudflare Detection Issue

**If you're getting "Turnstile challenge failed: 600010"**, you need to use the **stealth version** with Botright.

Regular Playwright is detected by Cloudflare. Use `axiom_auth_test_stealth.py` instead.

---

## Setup

1. **Install dependencies:**
   ```bash
   pip install playwright pytest-playwright botright
   python -m playwright install chromium --with-deps
   ```

2. **Configure environment:**
   - Copy `.env.example` to `.env` (if needed)
   - Add your axiom credentials (if automating login)

---

## 🚀 Quick Start (Stealth Mode - RECOMMENDED)

### **First time - Capture auth with Botright:**
```bash
cd playwright_tests
source ../venv/bin/activate
python axiom_auth_test_stealth.py
# Choose option 1
# Browser opens → Login manually → Botright bypasses Cloudflare → Auth saved
```

### **Reuse saved auth:**
```bash
python axiom_auth_test_stealth.py
# Choose option 2
# Already logged in automatically!
```

---

## Running Tests

### Run all tests:
```bash
pytest playwright_tests/
```

### Run specific test (from project root):
```bash
pytest playwright_tests/axiom_auth_test.py::test_axiom_auth_with_manual_login -s
```

### Run with visible browser (headed mode):
```bash
pytest playwright_tests/ --headed
```

---

## Test Files

### `axiom_auth_test_stealth.py` ⭐ **RECOMMENDED**
**Standalone stealth script using Botright** to bypass Cloudflare detection.

- Run directly: `python axiom_auth_test_stealth.py`
- Choose option 1: Manual login with auth capture
- Choose option 2: Reuse saved auth
- Saves to: `.auth/axiom_auth_botright.json`

### `axiom_auth_test.py`
Standard Playwright tests (may be blocked by Cloudflare):

1. **`test_axiom_authentication`** - Automated login (requires login selectors)
2. **`test_axiom_auth_with_manual_login`** - Manual login with auth capture
3. **`test_axiom_with_saved_auth`** - Reuse saved authentication

### `conftest.py`
Pytest configuration with fixtures for browser, context, and page management.

---

## Why Botright?

**Problem:** Cloudflare Turnstile detects regular Playwright:
- `navigator.webdriver = true` (dead giveaway)
- Missing browser fingerprints
- Automation-specific patterns

**Solution:** Botright wraps Playwright with stealth features:
- Hides `navigator.webdriver`
- Mimics real Chrome fingerprints
- Evades Cloudflare detection
- Drop-in replacement for Playwright

---

## Authentication State

### Capturing Auth (First Time):
```bash
python axiom_auth_test_stealth.py
# Select option 1
```

This will:
1. Open browser with stealth
2. Navigate to axiom.trade
3. Wait for you to login manually
4. Save cookies to `.auth/axiom_auth_botright.json`

### Reusing Auth:
```bash
python axiom_auth_test_stealth.py
# Select option 2
```

Once `.auth/axiom_auth_botright.json` exists, you can load it to skip login.

---

## Cookie Verification

The tests check for these cookies:
- `auth-access-token` - Your JWT access token
- `auth-refresh-token` - Your JWT refresh token
- `cf_clearance` - Cloudflare clearance cookie
- `__cf_bm` - Cloudflare bot management cookie

---

## Debugging

### View cookies in test:
```python
cookies = await page.context.cookies()
for cookie in cookies:
    print(f"{cookie['name']}: {cookie['value']}")
```

### Run with verbose output:
```bash
pytest playwright_tests/ -s -v
```

---

## Troubleshooting

### "Command 'pytest' not found"
You're not in the venv:
```bash
source venv/bin/activate  # From project root
```

### "Turnstile challenge failed: 600010"
Use the stealth version:
```bash
python playwright_tests/axiom_auth_test_stealth.py
```

### "No tests ran"
Make sure you're running from the correct directory:
```bash
# From project root:
pytest playwright_tests/axiom_auth_test.py::test_name -s

# From playwright_tests/:
pytest axiom_auth_test.py::test_name -s
```
