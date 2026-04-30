"""
src/main.py — Àṣẹ Agent entry point.

Full loop: push-to-talk → STT → parse → execute → English TTS response.
Run from the project root: python3 src/main.py
"""

import sys
import os
import subprocess

# Allow imports from project root (for config/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_recorder import AudioRecorder
from stt_engine import YorubaSTT
from command_parser import CommandParser
from mac_executor import MacExecutor
from config.settings import CONFIDENCE_THRESHOLD, TTS_VOICE, TTS_RATE


class YorubaAgent:
    def __init__(self):
        # Check Accessibility before loading heavy models
        if not MacExecutor.check_accessibility():
            sys.exit(1)

        self.recorder = AudioRecorder()
        self.stt = YorubaSTT()
        self.parser = CommandParser()
        self.executor = MacExecutor()

    # ── TTS ───────────────────────────────────────────────────────────────

    def speak(self, text: str):
        print(f"🔊 {text}")
        # macOS 'say' sounds natural. Samantha handles English perfectly.
        subprocess.run(["say", "-v", TTS_VOICE, "-r", str(TTS_RATE), text], check=False)

    # ── Result → spoken English ───────────────────────────────────────────

    def results_to_speech(self, results: list[str]) -> str:
        """Map ok/warn/error/unknown prefixes to spoken English phrases."""
        phrases = []
        for r in results:
            if r.startswith("ok:"):
                detail = r[3:]
                phrases.append(f"Done. {detail}")
            elif r.startswith("warn:"):
                phrases.append("I tried but couldn't complete it fully.")
            elif r.startswith("error:"):
                detail = r[6:]
                phrases.append(f"Error: {detail}")
            elif r.startswith("unknown:"):
                phrases.append("I didn't understand that. Please try again.")
        return ". ".join(phrases) if phrases else "Done."

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        print("=" * 52)
        print("🇳🇬  Àṣẹ Agent — Yoruba + English Voice Control")
        print("=" * 52)

        self.recorder.calibrate_noise_floor()
        self.speak("Welcome. I'm ready.")
        print("\n⌨️  Press ENTER to speak | Ctrl+C to quit\n")

        consecutive_low_confidence = 0

        while True:
            try:
                input("[ ENTER to speak ] ")

                # 1. Record
                audio, was_clipped = self.recorder.record_utterance()

                if audio is None:
                    self.speak("I didn't hear anything.")
                    continue

                if was_clipped:
                    self.speak("Please speak a little softer.")

                # 2. Transcribe
                stt_result = self.stt.transcribe(audio)
                text = stt_result["text"]
                confidence = stt_result["confidence"]
                language = stt_result.get("language", "?")

                if not text:
                    self.speak("I didn't catch that. Please try again.")
                    continue

                # Show detected language + confidence in terminal
                print(f"📝 [{language.upper()} {confidence:.0%}] {text}")

                # 3. Confidence gate
                if confidence < CONFIDENCE_THRESHOLD:
                    self.speak("Please say that again, I couldn't hear you clearly.")
                    consecutive_low_confidence += 1
                    if consecutive_low_confidence >= 3:
                        self.speak("Is your microphone working correctly?")
                        consecutive_low_confidence = 0
                    continue

                consecutive_low_confidence = 0

                # 4. Parse
                commands = self.parser.parse(stt_result)
                if not commands:
                    self.speak("I didn't understand what you wanted.")
                    continue

                print(f"⚙️  {len(commands)} command(s): {commands}")

                # 5. Execute
                results = self.executor.execute_queue(commands)
                print(f"   results: {results}")

                # 6. Respond
                self.speak(self.results_to_speech(results))

            except KeyboardInterrupt:
                self.speak("Goodbye!")
                print("\nBye! 👋")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                self.speak("Something went wrong. Please try again.")


if __name__ == "__main__":
    YorubaAgent().run()
