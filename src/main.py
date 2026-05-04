"""
src/main.py — Àṣẹ Agent entry point.

Full loop: wake-word/push-to-talk → STT → parse → execute → Yorùbá TTS response.
Run from the project root: python3 src/main.py

Options:
  --no-vlm        Skip loading the Vision-Language Model (saves ~4GB RAM)
  --no-wakeword   Disable wake word, use push-to-talk only
"""

import sys
import os
import argparse
import re
import threading

# Suppress macOS MallocStackLogging spam from subprocess/AppleScript
os.environ["MallocNanoZone"] = "0"
os.environ["MallocStackLogging"] = "0"

# Allow imports from project root (for config/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_recorder import AudioRecorder
from stt_engine import YorubaSTT
from tts_engine import YorubaTTS
from command_parser import CommandParser
from mac_executor import MacExecutor
from memory import AgentMemory
from wake_word import WakeWordEngine
from config.settings import CONFIDENCE_THRESHOLD


class YorubaAgent:
    def __init__(self, use_vlm=True, use_wakeword=True):
        # Check Accessibility before loading heavy models
        if not MacExecutor.check_accessibility():
            sys.exit(1)

        self.recorder = AudioRecorder()
        self.stt = YorubaSTT()
        self.tts = YorubaTTS()
        self.parser = CommandParser()
        self.executor = MacExecutor(use_vlm=use_vlm)
        self.memory = AgentMemory()
        self.wake_engine = WakeWordEngine() if use_wakeword else WakeWordEngine.__new__(WakeWordEngine)
        if not use_wakeword:
            self.wake_engine.is_ready = False
            print("⚠️  Wake word disabled via --no-wakeword. Using push-to-talk.")

    # ── TTS ───────────────────────────────────────────────────────────────

    def speak(self, text: str, blocking: bool = False):
        """Speak text. Non-blocking by default (daemon thread) for snappier UX."""
        if blocking:
            self.tts.speak(text)
        else:
            t = threading.Thread(target=self.tts.speak, args=(text,), daemon=True)
            t.start()

    # ── Result → spoken Yoruba ───────────────────────────────────────────

    def results_to_yoruba(self, results: list[str]) -> str:
        """Map ok/warn/error/unknown prefixes to spoken Yoruba phrases."""
        phrases = []
        for r in results:
            if r.startswith("ok:"):
                # "I have done it"
                phrases.append("Mo ti ṣe é")
            elif r.startswith("warn:"):
                # "I tried but it didn't work completely"
                phrases.append("Mo gbiyanju ṣugbọn ko ṣiṣẹ patapata")
            elif r.startswith("error:"):
                # "There was an error"
                phrases.append("Aṣiṣe kan wa")
            elif r.startswith("unknown:"):
                # "I don't understand, please speak again"
                phrases.append("Kò yé mi, jọwọ sọ lẹẹkansi")
        return ". ".join(phrases) if phrases else "O ti ṣe"

    # ── Language guard ────────────────────────────────────────────────────

    _ENGLISH_WORDS = re.compile(
        r"\b(the|has|been|have|was|is|are|opened|closed|done|successfully|"
        r"I|you|it|for|and|or|not|no|yes|please|already|found|started|"
        r"could|would|should|cannot|error|sorry|just|now|your|with)\b",
        re.IGNORECASE,
    )

    def _is_english(self, text: str) -> bool:
        """Return True if 3+ distinct common English words are detected."""
        matches = {m.group().lower() for m in self._ENGLISH_WORDS.finditer(text)}
        return len(matches) >= 3

    # ── Transparent ReAct (Thinking Out Loud) ─────────────────────────────
    
    def _speak_intermediate_thought(self, commands: list[dict]):
        """Speak a quick intermediate thought based on the first action to keep UX alive."""
        if not commands:
            return
            
        action = commands[0].get("action")
        target = commands[0].get("target", "")
        url = commands[0].get("url", "")
        query = commands[0].get("query", "")
        
        phrase = ""
        if action == "open_app":
            phrase = f"Mo ń ṣí {target}..."
        elif action == "open_website":
            domain = url.split("://")[-1].split("/")[0]
            phrase = f"Mo ń lọ sí {domain}..."
        elif action == "search_web":
            phrase = f"Mo ń wá {query} lórí ayelujara..."
        elif action == "search_files":
            phrase = f"Mo ń wá fáìlì..."
        elif action == "type_text":
            phrase = "Mo ń tẹ àwọn ọ̀rọ̀..."
        elif action == "take_screenshot":
            phrase = "Mo ń ya àwòrán..."
        elif action == "visual_click":
            phrase = "Mo ń wo ojú iwe naa..."
            
        if phrase:
            self.speak(phrase, blocking=False)

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        print("=" * 52)
        print("🇳🇬  Àṣẹ Agent — Yoruba + English Voice Control")
        print("=" * 52)

        self.recorder.calibrate_noise_floor()
        self.speak("Ẹ káàbọ̀. Mo ṣetan.")
        if self.wake_engine.is_ready:
            print("\n🎤 Say 'hey jarvis' to wake me up | Ctrl+C to quit\n")
        else:
            print("\n⌨️  Press ENTER to speak | Ctrl+C to quit\n")

        consecutive_low_confidence = 0

        while True:
            try:
                if self.wake_engine.is_ready:
                    # Continuous listening mode
                    self.recorder.listen_for_wake_word(self.wake_engine)
                    # Small beep or confirmation can be added here, but we will just speak:
                    self.speak("Mo wa pelu re")
                else:
                    # Push-to-talk fallback
                    input("\n[ ENTER to speak ] ")

                # 1. Record
                audio, was_clipped = self.recorder.record_utterance()

                if audio is None:
                    self.speak("Emi ko gbọ ohunkohun")
                    continue

                if was_clipped:
                    self.speak("Jọwọ sọ diẹ jẹjẹ diẹ sii")

                # 2. Transcribe
                stt_result = self.stt.transcribe(audio)
                text = stt_result["text"]
                confidence = stt_result["confidence"]
                language = stt_result.get("language", "?")

                if not text:
                    self.speak("Emi ko gbọ rẹ. Jọwọ sọ lẹẹkansi.")
                    continue

                # Show detected language + confidence in terminal
                print(f"📝 [{language.upper()} {confidence:.0%}] {text}")

                # 3. Confidence gate
                if confidence < CONFIDENCE_THRESHOLD:
                    self.speak("Jọwọ sọ lẹẹkansi, mi o gbọ o kedere")
                    consecutive_low_confidence += 1
                    if consecutive_low_confidence >= 3:
                        self.speak("Ṣe maikirofoonu ṣiṣẹ daradara?")
                        consecutive_low_confidence = 0
                    continue

                consecutive_low_confidence = 0

                # 4. Transparent ReAct Loop
                max_steps = 3
                step = 0
                all_results = []
                final_response = None
                current_stt = stt_result
                previous_commands = None
                
                while step < max_steps:
                    context = self.memory.get_recent_context()
                    commands = self.parser.parse(current_stt, memory_context=context)
                    
                    if not commands:
                        if step == 0:
                            self.speak("Emi ko ye ohun ti o fẹ")
                        break
                        
                    print(f"⚙️  Step {step+1}/{max_steps} | {len(commands)} command(s): {commands}")
                    
                    if len(commands) == 1 and commands[0].get("action") == "done":
                        final_response = commands[0].get("response")
                        break
                        
                    commands = [cmd for cmd in commands if cmd.get("action") != "done"]
                    if not commands:
                        break

                    # Speak intermediate thought to prevent UX freeze
                    self._speak_intermediate_thought(commands)

                    # 5. Execute
                    results = self.executor.execute_queue(commands)
                    print(f"   results: {results}")
                    all_results.extend(results)

                    # Save to Memory
                    self.memory.add_interaction(text, commands, results)
                    
                    # Prevent infinite retry loops
                    if commands == previous_commands and any(r.startswith("error:") for r in results):
                        print("⚠️  Action failed again — aborting retry loop.")
                        break
                    previous_commands = commands
                    
                    # On subsequent steps, use a synthetic prompt so the LLM
                    # focuses on context/results rather than re-interpreting
                    # the original speech.
                    current_stt = {
                        "text": "Continue the previous task based on the results.",
                        "is_code_switched": False,
                    }
                    
                    step += 1

                # 6. Respond (Dynamic)
                if final_response:
                    print(f"🗣️  Dynamic Response: {final_response}")
                    if self._is_english(final_response):
                        # LLM slipped into English — override with Yoruba
                        print("⚠️  Response detected as English — using Yoruba fallback")
                        self.speak(self.results_to_yoruba(all_results))
                    else:
                        self.speak(final_response)
                else:
                    self.speak(self.results_to_yoruba(all_results))

            except KeyboardInterrupt:
                self.executor.browser.stop()
                self.speak("O dabọ", blocking=True)  # blocking so farewell plays before exit
                print("\nBye! 👋")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                self.speak("Aṣiṣe kan wa")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Àṣẹ Agent — Yoruba Voice Assistant")
    arg_parser.add_argument("--no-vlm", action="store_true", help="Skip loading VLM (saves ~4GB RAM)")
    arg_parser.add_argument("--no-wakeword", action="store_true", help="Disable wake word, use push-to-talk")
    args = arg_parser.parse_args()

    YorubaAgent(
        use_vlm=not args.no_vlm,
        use_wakeword=not args.no_wakeword,
    ).run()
