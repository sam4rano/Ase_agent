"""
tests/test_parser.py — Unit tests for CommandParser JSON extraction + validation.

Tests cover all 4 extraction layers, multi-action, URL sanitization, and unknown commands.
Run: python3 -m pytest tests/test_parser.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

# Patch heavy MLX imports — we're testing parsing logic, not the model
with patch.dict("sys.modules", {
    "mlx_lm": MagicMock(),
    "mlx_lm.sample_utils": MagicMock(),
    "mlx": MagicMock(),
}):
    from src.command_parser import CommandParser


@pytest.fixture
def parser():
    """CommandParser with model loading and mdfind bypassed."""
    with patch.object(CommandParser, "__init__", lambda self, *a, **kw: None):
        p = CommandParser.__new__(CommandParser)
        p.installed_apps = ["Google Chrome", "Spotify", "Notes", "Safari", "Terminal"]
    return p


class TestJsonExtraction:

    def test_layer1_direct_json_array(self, parser):
        raw = '[{"action":"open_app","target":"Chrome"}]'
        result = parser._safe_parse_json(raw, "ṣi Chrome")
        assert result[0]["action"] == "open_app"

    def test_layer1_direct_json_object_wrapped_in_list(self, parser):
        raw = '{"action":"take_screenshot"}'
        result = parser._safe_parse_json(raw, "ya aworan")
        assert isinstance(result, list)
        assert result[0]["action"] == "take_screenshot"

    def test_layer2_markdown_fenced_json(self, parser):
        raw = '```json\n[{"action":"search_web","query":"Fela Kuti"}]\n```'
        result = parser._safe_parse_json(raw, "wa Fela Kuti")
        assert result[0]["query"] == "Fela Kuti"

    def test_layer3_json_array_embedded_in_prose(self, parser):
        raw = 'Here is the result: [{"action":"open_website","url":"https://youtube.com"}] done.'
        result = parser._safe_parse_json(raw, "lọ si youtube")
        assert result[0]["url"] == "https://youtube.com"

    def test_layer4_single_object_embedded(self, parser):
        raw = 'The command is {"action":"open_app","target":"Notes"} as requested.'
        result = parser._safe_parse_json(raw, "ṣi Notes")
        assert result[0]["target"] == "Notes"

    def test_fallback_unknown_on_garbage(self, parser):
        raw = "I am sorry I cannot parse that lol"
        result = parser._safe_parse_json(raw, "gibberish")
        assert result[0]["action"] == "unknown"
        assert result[0]["raw"] == "gibberish"

    def test_multi_action_preserved(self, parser):
        raw = '[{"action":"open_app","target":"Google Chrome"},{"action":"open_website","url":"https://youtube.com"}]'
        result = parser._safe_parse_json(raw, "ṣi Chrome lọ si youtube")
        assert len(result) == 2
        assert result[0]["action"] == "open_app"
        assert result[1]["action"] == "open_website"


class TestValidation:

    def test_unknown_action_blocked(self, parser):
        cmd = {"action": "shell_command", "cmd": "rm -rf /"}
        result = parser._validate(cmd)
        assert result["action"] == "unknown"

    def test_url_without_scheme_gets_https(self, parser):
        cmd = {"action": "open_website", "url": "youtube.com"}
        result = parser._validate(cmd)
        assert result["url"] == "https://youtube.com"

    def test_javascript_url_blocked(self, parser):
        cmd = {"action": "open_website", "url": "javascript:alert(1)"}
        result = parser._validate(cmd)
        assert result["action"] == "unknown"

    def test_file_url_blocked(self, parser):
        cmd = {"action": "open_website", "url": "file:///etc/passwd"}
        result = parser._validate(cmd)
        assert result["action"] == "unknown"

    def test_https_url_passes(self, parser):
        cmd = {"action": "open_website", "url": "https://github.com"}
        result = parser._validate(cmd)
        assert result["url"] == "https://github.com"


class TestFuzzyMatch:

    def test_exact_match(self, parser):
        assert parser._fuzzy_match_app("Google Chrome") == "Google Chrome"

    def test_partial_match_request_in_installed(self, parser):
        # "Chrome" is in "Google Chrome"
        assert parser._fuzzy_match_app("Chrome") == "Google Chrome"

    def test_partial_match_installed_in_request(self, parser):
        # "Safari" is in "Open Safari Browser"
        result = parser._fuzzy_match_app("Open Safari Browser")
        assert result == "Safari"

    def test_unknown_app_returned_as_is(self, parser):
        result = parser._fuzzy_match_app("SuperFakeApp9000")
        assert result == "SuperFakeApp9000"

    def test_case_insensitive_match(self, parser):
        assert parser._fuzzy_match_app("spotify") == "Spotify"
