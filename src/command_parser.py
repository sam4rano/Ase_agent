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

_SYSTEM_PROMPT = """You are a command parser for a Yoruba-language voice assistant. The user speaks Yoruba or mixed Yoruba-English.
Return ONLY a JSON array of command objects. No markdown, no explanation, just raw JSON.

You may be given recent conversation and action history. Use this context if the user refers to previous actions (like "pa á" (close it), "sọkalẹ" (scroll down), etc).

Each command object must have an "action" field. Supported actions:
{"action":"open_app","target":"AppName"}
{"action":"close_app","target":"AppName"}
{"action":"open_website","url":"https://..."}
{"action":"search_web","query":"search terms"}
{"action":"search_files","query":"filename or keyword"}
{"action":"type_text","text":"text to type"}
{"action":"take_screenshot"}
{"action":"visual_click","element_name":"name of button or link"}
{"action":"done", "response":"<YORUBA ONLY response>"}
{"action":"unknown","raw":"original text"}

CRITICAL RULE: The "response" field inside a "done" action MUST ALWAYS be written in Yoruba language. NEVER use English in the response field. Examples of correct Yoruba responses:
- "Mo ti ṣí Google Chrome fún ọ" (I have opened Google Chrome for you)
- "Mo ti wá 'Fela Kuti' fún ọ" (I have searched for Fela Kuti for you)
- "Mo ti ya àwòrán fún ọ" (I have taken a screenshot for you)
- "Àṣìṣe kan wà" (There was an error)

If you need to perform multiple steps, output the first set of actions. The system will run them and call you again with results. When fully done, output [{"action":"done", "response":"(Yoruba confirmation)"}].
CRITICAL RULE 2: If the previous results show an error, DO NOT retry the exact same failing action. Instead, output a "done" action explaining the error to the user.

If the user gives multiple instructions, return multiple objects in the array.

Examples:
"ṣi Chrome" → [{"action":"open_app","target":"Google Chrome"}]
"play búkọlábẹ̀kì song" or "ṣi orin" → [{"action":"search_web","query":"bukola bekes song youtube"}]
"lọ si youtube.com" → [{"action":"open_website","url":"https://youtube.com"}]
"pa á" or "close it" → [{"action":"close_app","target":"AppName"}] (infer AppName from context)
"tẹ play lori youtube" → [{"action":"visual_click","element_name":"play button"}]
"ṣi Chrome ki o si lọ si youtube" → [{"action":"open_app","target":"Google Chrome"},{"action":"open_website","url":"https://youtube.com"}]
"wa fún mi nipa Fela Kuti" → [{"action":"search_web","query":"Fela Kuti"}]
"ya aworan" → [{"action":"take_screenshot"}]
When a task finishes successfully (e.g. opened Discord): [{"action":"done","response":"Mo ti ṣí Discord fún ọ"}]

Return ONLY the JSON array. Do not wrap in markdown."""


class CommandParser:
    def __init__(self, model_id: str = LLM_MODEL_ID):
        print(f"🧠 Loading LLM ({model_id.split('/')[-1]})...")
        self.model, self.tokenizer = load(model_id)
        self.installed_apps = self._get_installed_apps()
        print(f"✅ LLM ready — {len(self.installed_apps)} installed apps indexed")

    def parse(self, stt_result: dict, memory_context: str = "") -> list[dict]:
        """
        Convert an STT result dict into a list of command dicts.
        Each dict has at minimum {"action": str}.
        """
        text = stt_result["text"]
        is_code_switched = stt_result.get("is_code_switched", False)

        user_content = ""
        if memory_context and memory_context != "No previous context.":
            user_content += f"{memory_context}\n\n"

        user_content += f"User said: {text}"
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
        arr = re.search(r"\[.*\]", raw, re.DOTALL)
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

        if action in ("open_app", "close_app") and "target" in cmd:
            cmd["target"] = self._fuzzy_match_app(cmd["target"])

        if action == "open_website" and "url" in cmd:
            url = cmd["url"]
            # Block known dangerous schemes first
            dangerous = ("javascript:", "data:", "file:", "ftp:", "blob:")
            if any(url.lower().startswith(s) for s in dangerous):
                print(f"⚠️  Blocked dangerous URL: {url!r}")
                return {"action": "unknown", "raw": url}
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
        Priority: exact → partial containment (shortest wins) → original (let executor error).
        """
        req_lower = requested.lower()

        # Exact
        for app in self.installed_apps:
            if app.lower() == req_lower:
                return app

        # Partial containment (either direction) — prefer shortest match
        candidates = []
        for app in self.installed_apps:
            if req_lower in app.lower() or app.lower() in req_lower:
                candidates.append(app)

        if candidates:
            # Shortest name is most likely the canonical app (e.g., "Safari" over "Safari Technology Preview")
            return min(candidates, key=len)

        print(f"⚠️  App '{requested}' not found in installed apps — trying anyway")
        return requested
