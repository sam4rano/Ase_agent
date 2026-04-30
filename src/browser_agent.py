"""
src/browser_agent.py

Headless/UI browser automation using Playwright.
Works in tandem with VLM Engine to click visually grounded elements.
"""

import time
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class BrowserAgent:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright_context = None

        if not PLAYWRIGHT_AVAILABLE:
            print("⚠️ Playwright not installed. Browser automation disabled.")
            return

    def start(self):
        """Start the browser."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
            
        print("🌐 Starting Playwright browser...")
        try:
            self.playwright_context = sync_playwright().start()
            # We use chromium by default
            self.browser = self.playwright_context.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
            return True
        except Exception as e:
            print(f"⚠️ Failed to start Playwright: {e}")
            print("   (Did you run 'playwright install chromium'?)")
            return False

    def navigate(self, url: str) -> str:
        if not self.page:
            if not self.start():
                return "error: Browser could not start"
                
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"ok: Navigated to {url}"
        except PlaywrightTimeoutError:
            return f"warn: Navigated to {url} but page load timed out"
        except Exception as e:
            return f"error: Navigation failed - {e}"

    def take_screenshot(self, path: str) -> str:
        """Take a screenshot of the current viewport."""
        if not self.page:
            return "error: Browser not active"
        try:
            self.page.screenshot(path=path)
            return f"ok: Browser screenshot saved to {path}"
        except Exception as e:
            return f"error: Screenshot failed - {e}"

    def click_coordinates(self, x: int, y: int) -> str:
        """Click specific coordinates determined by the VLM."""
        if not self.page:
            return "error: Browser not active"
        try:
            self.page.mouse.click(x, y)
            time.sleep(1) # wait for action to register
            return f"ok: Clicked at ({x}, {y})"
        except Exception as e:
            return f"error: Click failed - {e}"
            
    def click_selector(self, selector: str) -> str:
        """Fallback: traditional DOM-based click."""
        if not self.page:
            return "error: Browser not active"
        try:
            self.page.click(selector, timeout=5000)
            return f"ok: Clicked selector '{selector}'"
        except Exception as e:
            return f"error: Could not click '{selector}'"

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright_context:
            self.playwright_context.stop()
