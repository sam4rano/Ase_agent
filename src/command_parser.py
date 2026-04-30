"""
src/command_parser.py

MLX Qwen2.5-1.5B command parser: Yoruba/code-switched text → JSON action list.
Handles: multi-action, markdown-wrapped JSON, hallucinated app names, malformed URLs.
"""

import json
import re
import subprocess
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

from config.settings import (
    LLM_MODEL_ID,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    ALLOWED_ACTIONS,
    ALLOWED_URL_SCHEMES,
)

_SYSTEM_PROMPT = """You are a command parser. The user speaks Yoruba or mixed Yoruba-English.
Return ONLY a JSON array of command objects. No markdown, no explanation, just raw JSON.

Each command object must have an "action" field. Supported actions:
{"action":"open_app","target":"AppName"}
{"action":"open_website","url":"https://..."}
{"action":"search_web","query":"search terms"}
{"action":"search_files","query":"filename or keyword"}
{"action":"type_text","text":"text to type"}
{"action":"take_screenshot"}
{"action":"unknown","raw":"original text"}

If the user gives multiple instructions, return multiple objects in the array.

Examples:
"ṣi Chrome" → [{"action":"open_app","target":"Google Chrome"}]
"lọ si youtube.com" → [{"action":"open_website","url":"https://youtube.com"}]
"ṣi Chrome ki o si lọ si youtube" → [{"action":"open_app","target":"Google Chrome"},{"action":"open_website","url":"https://youtube.com"}]
"wa fún mi nipa Fela Kuti" → [{"action":"search_web","query":"Fela Kuti"}]
"ya aworan" → [{"action":"take_screenshot"}]

Return ONLY the JSON array. Do not wrap in markdown."""


class CommandParser:
    def __init__(self, model_id: str = LLM_MODEL_ID):
        print(f"🧠 Loading LLM ({model_id.split('/')[-1]})...")
        self.model, self.tokenizer = load(model_id)
        self.installed_apps = self._get_installed_apps()
        print(f"✅ LLM ready — {len(self.installed_apps)} installed apps indexed")

    def parse(self, stt_result: dict) -> list[dict]:
        """
        Convert an STT result dict into a list of command dicts.
        Each dict has at minimum {"action": str}.
        """
        text = stt_result["text"]
        is_code_switched = stt_result.get("is_code_switched", False)

        user_content = f"User said: {text}"
        if is_code_switched:
            user_content += "\n(Note: this is mixed Yoruba-English speech)"

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        raw = generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=LLM_MAX_TOKENS,
            sampler=make_sampler(temp=LLM_TEMPERATURE),
        ).strip()

        commands = self._safe_parse_json(raw, text)
        return [self._validate(cmd) for cmd in commands]

    # ── JSON extraction ───────────────────────────────────────────────────

    def _safe_parse_json(self, raw: str, original_text: str) -> list:
        """
        4-layer JSON extraction. LLMs are unreliable about formatting.
        Layer 1: direct parse
        Layer 2: strip markdown fences then parse
        Layer 3: regex-extract first JSON array
        Layer 4: regex-extract first JSON object
        Fallback: return unknown command
        """
        # Layer 1
        try:
            r = json.loads(raw)
            return r if isinstance(r, list) else [r]
        except json.JSONDecodeError:
            pass

        # Layer 2
        fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        # Layer 3
        arr = re.search(r"\[.*?\]", raw, re.DOTALL)
        if arr:
            try:
                return json.loads(arr.group())
            except json.JSONDecodeError:
                pass

        # Layer 4
        obj = re.search(r"\{.*?\}", raw, re.DOTALL)
        if obj:
            try:
                return [json.loads(obj.group())]
            except json.JSONDecodeError:
                pass

        print(f"⚠️  Could not parse LLM output: {raw[:120]!r}")
        return [{"action": "unknown", "raw": original_text}]

    # ── Validation ────────────────────────────────────────────────────────

    def _validate(self, cmd: dict) -> dict:
        """
        Sanitize a parsed command:
        - Reject unknown action types
        - Fuzzy-match app names against installed apps
        - Ensure URLs have a valid scheme (blocks javascript:, file://, etc.)
        """
        action = cmd.get("action", "unknown")

        if action not in ALLOWED_ACTIONS:
            print(f"⚠️  Blocked disallowed action: {action!r}")
            return {"action": "unknown", "raw": str(cmd)}

        if action == "open_app" and "target" in cmd:
            cmd["target"] = self._fuzzy_match_app(cmd["target"])

        if action == "open_website" and "url" in cmd:
            url = cmd["url"]
            if not url.startswith(ALLOWED_URL_SCHEMES):
                # Try to rescue a bare domain
                if "://" not in url:
                    cmd["url"] = "https://" + url
                else:
                    print(f"⚠️  Blocked non-HTTP URL: {url!r}")
                    return {"action": "unknown", "raw": url}

        return cmd

    # ── App name fuzzy matching ───────────────────────────────────────────

    def _get_installed_apps(self) -> list[str]:
        """Return list of installed .app names (without extension)."""
        try:
            result = subprocess.run(
                ["mdfind", "kMDItemKind == 'Application'"],
                capture_output=True, text=True, timeout=5,
            )
            return [
                line.split("/")[-1].replace(".app", "")
                for line in result.stdout.strip().split("\n")
                if line.endswith(".app")
            ]
        except Exception as e:
            print(f"⚠️  Could not index installed apps: {e}")
            return []

    def _fuzzy_match_app(self, requested: str) -> str:
        """
        Match LLM-returned app name against installed apps.
        Priority: exact → partial containment → original (let executor error).
        """
        req_lower = requested.lower()

        # Exact
        for app in self.installed_apps:
            if app.lower() == req_lower:
                return app

        # Partial containment (either direction)
        for app in self.installed_apps:
            if req_lower in app.lower() or app.lower() in req_lower:
                return app

        print(f"⚠️  App '{requested}' not found in installed apps — trying anyway")
        return requested
