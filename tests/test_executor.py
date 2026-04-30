"""
tests/test_executor.py — Unit tests for MacExecutor.

All AppleScript and subprocess calls are mocked — no real apps are opened.
Run: python3 -m pytest tests/test_executor.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

# Patch heavy imports before loading MacExecutor
with patch.dict("sys.modules", {
    "browser_agent": MagicMock(),
    "vlm_engine": MagicMock(),
}):
    from src.mac_executor import MacExecutor


@pytest.fixture
def executor():
    """MacExecutor with BrowserAgent + VLMEngine bypassed."""
    with patch.object(MacExecutor, "__init__", lambda self: None):
        e = MacExecutor.__new__(MacExecutor)
        e.browser = MagicMock()
        e.vlm = MagicMock()
        e.vlm.is_ready = False
    return e


class TestExecuteOne:

    def test_unknown_action_returns_error(self, executor):
        result = executor._execute_one({"action": "shell_command", "cmd": "rm -rf /"})
        assert result.startswith("error:")

    def test_unknown_unknown_returns_unknown(self, executor):
        result = executor._execute_one({"action": "unknown", "raw": "some gibberish"})
        assert result.startswith("unknown:")

    def test_missing_field_returns_error(self, executor):
        # open_app requires "target"
        result = executor._execute_one({"action": "open_app"})
        assert result.startswith("error:")


class TestOpenApp:

    def test_open_app_success(self, executor):
        with patch.object(executor, "_applescript") as mock_as:
            # activate call succeeds, then process check returns "true"
            mock_as.side_effect = [
                ("", True),    # activate
                ("true", True),  # process check
            ]
            with patch("time.sleep"):
                result = executor.open_app("Safari")
        assert result.startswith("ok:")
        assert "Safari" in result

    def test_open_app_applescript_fails_shell_fallback(self, executor):
        with patch.object(executor, "_applescript") as mock_as, \
             patch("subprocess.run") as mock_run, \
             patch("time.time", side_effect=[0, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.1]), \
             patch("time.sleep"):
            mock_as.side_effect = [
                ("", False),    # activate fails
                ("true", True), # process check succeeds on second poll
            ]
            mock_run.return_value = MagicMock(returncode=0)
            result = executor.open_app("FakeApp")
        # Should have tried shell fallback and verified
        assert not result.startswith("error:App 'FakeApp' not found")

    def test_open_app_not_found(self, executor):
        with patch.object(executor, "_applescript", return_value=("", False)), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)), \
             patch("time.sleep"):
            result = executor.open_app("TotallyFakeApp")
        assert "not found" in result


class TestCloseApp:

    def test_close_app_success(self, executor):
        with patch.object(executor, "_applescript", return_value=("", True)):
            result = executor.close_app("Safari")
        assert result.startswith("ok:")
        assert "Closed Safari" in result

    def test_close_app_fallback_killall(self, executor):
        with patch.object(executor, "_applescript", return_value=("", False)), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = executor.close_app("Safari")
        assert result.startswith("ok:")

    def test_close_app_failure(self, executor):
        with patch.object(executor, "_applescript", return_value=("", False)), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = executor.close_app("GhostApp")
        assert result.startswith("error:")


class TestSearchWeb:

    def test_search_web_uses_browser_navigate(self, executor):
        executor.browser.navigate.return_value = "ok: Navigated to https://www.google.com/search?q=Fela%20Kuti"
        result = executor.search_web("Fela Kuti")
        assert "ok:" in result
        executor.browser.navigate.assert_called_once()
        call_url = executor.browser.navigate.call_args[0][0]
        assert "google.com/search" in call_url


class TestVisualClick:

    def test_visual_click_no_browser(self, executor):
        executor.browser.page = None
        result = executor.visual_click("play button")
        assert "error" in result

    def test_visual_click_vlm_not_ready_falls_back_to_dom(self, executor):
        executor.browser.page = MagicMock()
        executor.vlm.is_ready = False
        executor.browser.click_selector.return_value = "ok: Clicked selector 'text=play button'"
        result = executor.visual_click("play button")
        assert "ok:" in result
        executor.browser.click_selector.assert_called_once()


class TestExecuteQueue:

    def test_queue_executes_all_commands(self, executor):
        commands = [
            {"action": "open_app", "target": "Safari"},
            {"action": "search_web", "query": "test"},
        ]
        with patch.object(executor, "_execute_one", return_value="ok:done") as mock_exec, \
             patch("time.sleep"):
            results = executor.execute_queue(commands)

        assert mock_exec.call_count == 2
        assert all(r == "ok:done" for r in results)
