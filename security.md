# Àṣẹ Agent — Security Model

> This document defines the threat model, known attack surfaces, and mitigations for the Àṣẹ Agent.
> Update this file whenever a new execution capability is added.

---

## 1. Threat Model

The agent runs locally on your Mac. It has three powerful capabilities:

| Capability | What it can do |
|---|---|
| AppleScript execution | Open apps, control UI, simulate keystrokes |
| `subprocess` calls | Run shell commands as the current user |
| URL opening | Navigate any URL in Chrome |

**Attacker profile we defend against:**
- Malicious audio input (someone speaks a destructive command nearby)
- LLM hallucination producing dangerous commands (e.g., `rm -rf`)
- URL injection via a crafted voice command
- Scope creep (the agent doing more than asked)

**We do NOT defend against:**
- A compromised macOS system
- A malicious Python package in the environment
- An attacker with physical/shell access to the machine

---

## 2. Attack Surfaces & Mitigations

### 2.1 URL Injection

**Risk:** User speaks a URL that redirects to a phishing/malware site. The executor opens it blindly.

**Mitigation:**
- All URLs are opened in Chrome's existing session (not a new profile)
- URLs must start with `http://` or `https://` — bare protocol (`javascript:`, `file://`) is blocked
- URL is passed through `urllib.parse.quote` for search queries (prevents injection into Google URLs)

**What we don't do:** We don't block specific domains — that's too brittle and paternalistic for a personal assistant.

```python
# In mac_executor.py — enforced
if not url.startswith(("http://", "https://")):
    return "error:Blocked non-HTTP URL"
```

---

### 2.2 Shell Injection via App Names

**Risk:** LLM returns `app_name = 'Chrome"; rm -rf ~; echo "'`, which AppleScript or `open -a` executes.

**Mitigation:**
- AppleScript strings are **not shell-interpolated** — they go through `osascript -e` as a raw string argument, not through `sh -c`
- The `open -a <app_name>` call uses `subprocess.run(["open", "-a", app_name], ...)` with a list, never a shell string — this prevents shell word-splitting
- App names are fuzzy-matched against `mdfind`'s installed app list before execution — unknown names go through but produce an error, not a shell command

```python
# SAFE — list form, not shell string
subprocess.run(["open", "-a", app_name], capture_output=True)

# NEVER do this
subprocess.run(f"open -a {app_name}", shell=True)  # ← shell injection vector
```

---

### 2.3 AppleScript Keystroke Injection

**Risk:** The `type_text` action simulates keystrokes. If the LLM hallucinates a destructive key sequence (e.g., `⌘Q` repeated), it could close apps or trigger shortcuts.

**Mitigation:**
- `type_text` only calls `keystroke` with plain text characters — no modifier keys (`command`, `control`, etc.) are passed
- The `search_files` action uses `keystroke space using command down` (Spotlight) — this is the only hardcoded modifier key usage, and it's in a fixed string, not user-controlled

**Accepted risk:** A user could say "type Command Q" and the LLM might return it as text — but `pyttsx3` keystrokes don't support modifier combinations via the `text` field (those require explicit AppleScript modifier syntax).

---

### 2.4 LLM Hallucination — Destructive Commands

**Risk:** LLM returns `{"action": "shell_command", "cmd": "rm -rf /"}` or similar invented action types.

**Mitigation:**
- The executor uses an **explicit allowlist** of action types. Anything not on the list returns `error:Unknown action`
- There is **no `shell_command` action** and there never will be — it must be added explicitly with a code review

```python
ALLOWED_ACTIONS = {
    "open_app", "open_website", "search_web",
    "search_files", "type_text", "take_screenshot", "unknown"
}

if action not in ALLOWED_ACTIONS:
    return f"error:Unknown action {action}"
```

---

### 2.5 Ambient Audio Attack

**Risk:** Someone in earshot says "ṣi terminal ki o si pa faili gbogbo" (*"open terminal and delete all files"*) while push-to-talk is held.

**Mitigation:**
- Push-to-talk is **ENTER key only** — requires physical keyboard access
- There is no wake-word or always-on recording; the mic is only active while the key is held
- This is the strongest mitigation: the attack requires the attacker to be at the keyboard

**Accepted risk:** Anyone at the keyboard can trigger any command. This is a personal assistant, not a shared-system agent.

---

### 2.6 macOS Permission Escalation

**Risk:** Agent tries to access areas beyond its macOS sandbox (e.g., Keychain, camera, contacts).

**Mitigation:**
- The agent requests exactly two macOS permissions:
  1. **Microphone** — for `sounddevice` recording
  2. **Accessibility** — for AppleScript UI control
- No Keychain access, no camera, no contacts, no location
- Both permissions are user-granted through System Settings and can be revoked at any time

**How to revoke:**
```
System Settings → Privacy & Security → Microphone → toggle off "Terminal" (or your Python env)
System Settings → Privacy & Security → Accessibility → remove your app
```

---

### 2.7 Model Integrity

**Risk:** A tampered model file produces malicious outputs.

**Mitigation:**
- Models are downloaded from `mlx-community` on HuggingFace — a verified, community-reviewed namespace
- HuggingFace uses SHA-256 file hashes for all model files; `huggingface_hub` verifies these on download
- After first download, models are cached locally in `~/.cache/huggingface/` — subsequent loads skip the network

---

## 3. Permissions Required (and Why)

| Permission | Required by | Purpose | How to grant |
|---|---|---|---|
| Microphone | `sounddevice` | Record voice commands | System Settings → Privacy → Microphone |
| Accessibility | `osascript` | Control apps via AppleScript | System Settings → Privacy → Accessibility |
| Full Disk Access | **NOT required** | — | — |
| Contacts / Calendar | **NOT required** | — | — |
| Camera | **NOT required** | — | — |

The agent **will fail gracefully** if either required permission is missing, printing a clear error message before the main loop starts.

---

## 4. What the Agent Will Never Do

These are hardcoded exclusions, not configurable:

- ❌ Execute shell commands as a string (`shell=True`)
- ❌ Use `eval()` or `exec()` on any LLM output
- ❌ Access `file://` URLs
- ❌ Open URLs with non-HTTP protocols (`javascript:`, `ftp:`, `data:`, etc.)
- ❌ Pass user text through `sh -c` or `bash -c`
- ❌ Perform any network request except model downloads at startup

---

## 5. Logging & Audit

- All executed commands are printed to stdout with a `⚙️` prefix
- All errors are printed with a `⚠️` or `❌` prefix
- No logs are written to disk by default (reduces attack surface of log files)
- To enable persistent logging, redirect stdout: `python main.py >> ase_agent.log 2>&1`

---

## 6. Security Checklist Before Running

- [ ] Python environment is isolated (`python -m venv venv`)
- [ ] `requirements.txt` is pinned (no `>=` or `*` version specs)
- [ ] Microphone permission granted in System Settings
- [ ] Accessibility permission granted in System Settings
- [ ] You understand that anyone at the keyboard can trigger commands

---

*Last updated: 2026-04-30*
