"""
tests/test_executor.py — Unit tests for MacExecutor.

All AppleScript and subprocess calls are mocked — no real apps are opened.
Run: python3 -m pytest tests/test_executor.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

from src.mac_executor import MacExecutor


@pytest.fixture
def executor():
    return MacExecutor()


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


class TestOpenWebsite:

    def test_open_website_success(self, executor):
        with patch.object(executor, "open_app", return_value="ok:Opened Google Chrome"), \
             patch.object(executor, "_applescript", return_value=("", True)), \
             patch("time.sleep"):
            result = executor.open_website_in_chrome("https://example.com")
        assert result.startswith("ok:")

    def test_open_website_fallback_on_applescript_fail(self, executor):
        with patch.object(executor, "open_app", return_value="ok:Opened Google Chrome"), \
             patch.object(executor, "_applescript", return_value=("", False)), \
             patch("subprocess.run"), \
             patch("time.sleep"):
            result = executor.open_website_in_chrome("https://example.com")
        assert result.startswith("ok:")


class TestSearchWeb:

    def test_search_web_encodes_query(self, executor):
        captured_urls = []

        def fake_open(url):
            captured_urls.append(url)
            return "ok:opened"

        with patch.object(executor, "open_website_in_chrome", side_effect=fake_open):
            executor.search_web("Fela Kuti music")

        assert "Fela+Kuti+music" in captured_urls[0] or "Fela%20Kuti" in captured_urls[0]
        assert "google.com/search" in captured_urls[0]


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
