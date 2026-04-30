"""
src/mac_executor.py

AppleScript + subprocess executor with result verification and error recovery.
All actions return a prefixed string: "ok:", "warn:", or "error:".
"""

import subprocess
import time
import urllib.parse
import getpass
import os

from browser_agent import BrowserAgent
from vlm_engine import VLMEngine

from config.settings import (
    ALLOWED_ACTIONS,
    APP_VERIFY_TIMEOUT,
    APP_VERIFY_POLL,
    INTER_COMMAND_DELAY,
    CHROME_OPEN_WAIT,
)

_USER = getpass.getuser()


class MacExecutor:
    def __init__(self):
        self.browser = BrowserAgent(headless=False)
        self.vlm = VLMEngine()

    # ── Public API ────────────────────────────────────────────────────────

    def execute_queue(self, commands: list[dict]) -> list[str]:
        """
        Execute a list of commands in sequence.
        Returns a list of result strings, one per command.
        """
        results = []
        for cmd in commands:
            result = self._execute_one(cmd)
            results.append(result)
            time.sleep(INTER_COMMAND_DELAY)
        return results

    # ── Dispatcher ────────────────────────────────────────────────────────

    def _execute_one(self, cmd: dict) -> str:
        action = cmd.get("action")
        if action not in ALLOWED_ACTIONS:
            return f"error:Unknown action '{action}'"
        try:
            if action == "open_app":
                return self.open_app(cmd["target"])
            elif action == "close_app":
                return self.close_app(cmd["target"])
            elif action == "open_website":
                return self.browser.navigate(cmd["url"])
            elif action == "search_web":
                return self.search_web(cmd["query"])
            elif action == "search_files":
                return self.search_files(cmd["query"])
            elif action == "type_text":
                return self.type_text(cmd["text"])
            elif action == "take_screenshot":
                return self.take_screenshot()
            elif action == "visual_click":
                return self.visual_click(cmd["element_name"])
            elif action == "unknown":
                return f"unknown:{cmd.get('raw', '')}"
        except KeyError as e:
            return f"error:Missing field {e} in command {cmd}"
        except Exception as e:
            return f"error:{e}"

    # ── Actions ───────────────────────────────────────────────────────────

    def open_app(self, app_name: str) -> str:
        """Open an app and verify it is running within APP_VERIFY_TIMEOUT seconds."""
        _, success = self._applescript(f'tell application "{app_name}" to activate')
        if not success:
            # Fallback: shell open
            r = subprocess.run(["open", "-a", app_name], capture_output=True)
            if r.returncode != 0:
                return f"error:App '{app_name}' not found"

        # Verify the process is actually running
        deadline = time.time() + APP_VERIFY_TIMEOUT
        while time.time() < deadline:
            time.sleep(APP_VERIFY_POLL)
            check, _ = self._applescript(
                f'tell application "System Events" to return '
                f'(name of processes) contains "{app_name}"'
            )
            if check.lower() == "true":
                return f"ok:Opened {app_name}"

        return f"warn:Launched {app_name} but could not verify it is running"

    def close_app(self, app_name: str) -> str:
        """Close an app gracefully."""
        _, success = self._applescript(f'tell application "{app_name}" to quit')
        if success:
            return f"ok:Closed {app_name}"
        
        # Fallback: killall
        r = subprocess.run(["killall", app_name], capture_output=True)
        if r.returncode == 0:
            return f"ok:Force closed {app_name}"
            
        return f"error:Could not close {app_name}"

    def open_website_in_chrome(self, url: str) -> str:
        """(Deprecated) AppleScript navigation, now handled by browser_agent."""
        pass

    def search_web(self, query: str) -> str:
        """Google-search for query in Chrome."""
        encoded = urllib.parse.quote(query)
        return self.open_website_in_chrome(f"https://www.google.com/search?q={encoded}")

    def search_files(self, query: str) -> str:
        """Use mdfind (Spotlight CLI) and open Spotlight UI with the query."""
        try:
            result = subprocess.run(
                ["mdfind", "-name", query, "-onlyin", f"/Users/{_USER}"],
                capture_output=True, text=True, timeout=5,
            )
            files = [f for f in result.stdout.strip().split("\n") if f][:10]
        except subprocess.TimeoutExpired:
            files = []

        # Open Spotlight visually too
        self._applescript(f'''
            tell application "System Events"
                keystroke space using command down
                delay 0.4
                keystroke "{query}"
            end tell
        ''')

        count = len(files)
        return f"ok:Found {count} file(s) — Spotlight opened" if count else "warn:No files found — Spotlight opened"

    def type_text(self, text: str) -> str:
        """Type plain text at the current cursor position."""
        # Escape backslashes and double-quotes for AppleScript string
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
        _, success = self._applescript(
            f'tell application "System Events" to keystroke "{safe_text}"'
        )
        return "ok:Text typed" if success else "error:Could not type text"

    def take_screenshot(self) -> str:
        """Interactive screenshot selection saved to Desktop."""
        path = f"/Users/{_USER}/Desktop/screenshot_{int(time.time())}.png"
        result = subprocess.run(["screencapture", "-i", path], capture_output=True)
        if result.returncode == 0:
            return f"ok:Screenshot saved to Desktop"
        return "warn:Screenshot cancelled"

    def visual_click(self, element_name: str) -> str:
        """
        Uses VLM to find element_name in the browser, then clicks it via Playwright.
        """
        if not self.browser.page:
            return "error: Browser not running. Navigate to a URL first."
            
        if not self.vlm.is_ready:
            # Fallback to DOM click if VLM isn't loaded (e.g., M1 constraints)
            print("⚠️ VLM not loaded. Falling back to DOM selector click.")
            # A naive heuristic for DOM fallback:
            return self.browser.click_selector(f"text={element_name}")

        screenshot_path = f"/tmp/vlm_screenshot_{int(time.time())}.png"
        res = self.browser.take_screenshot(screenshot_path)
        if "error" in res:
            return res

        print(f"👁️  Asking VLM to find '{element_name}'...")
        coords_str = self.vlm.find_element_coordinates(screenshot_path, element_name)
        print(f"   VLM replied: {coords_str}")
        
        # Parse coordinates (assuming VLM returns e.g., "x: 100, y: 200" or similar)
        # This is highly dependent on the VLM's output format.
        # For robustness in this implementation, we attempt to parse integers.
        import re
        nums = re.findall(r'\d+', coords_str)
        if len(nums) >= 2:
            x, y = int(nums[0]), int(nums[1])
            return self.browser.click_coordinates(x, y)
        else:
            return f"error: VLM could not find distinct coordinates for '{element_name}'. Reply: {coords_str}"

    # ── Helpers ───────────────────────────────────────────────────────────

    def _applescript(self, script: str) -> tuple[str, bool]:
        """Run an AppleScript and return (stdout, success)."""
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True,
        )
        success = result.returncode == 0
        if not success:
            print(f"⚠️  AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip(), success

    @staticmethod
    def check_accessibility() -> bool:
        """Return True if Accessibility permission is granted."""
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to return name of first process'],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(
                "❌ Accessibility permission not granted.\n"
                "   System Settings → Privacy & Security → Accessibility → add Terminal"
            )
            return False
        return True
