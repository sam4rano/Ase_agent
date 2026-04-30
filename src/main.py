"""
src/main.py — Àṣẹ Agent entry point.

Full loop: push-to-talk → STT → parse → execute → Yoruba TTS response.
Run from the project root: python3 src/main.py
"""

import sys
import os

# Allow imports from project root (for config/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess

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
        # macOS 'say' sounds human, pyttsx3 sounds robotic.
        # -v: voice, -r: words-per-minute. Falls back silently if say is unavailable.
        subprocess.run(["say", "-v", TTS_VOICE, "-r", str(TTS_RATE), text], check=False)

    # ── Result → Yoruba phrases ───────────────────────────────────────────

    def results_to_yoruba(self, results: list[str]) -> str:
        """Map ok/warn/error/unknown prefixes to natural Yoruba phrases."""
        phrases = []
        for r in results:
            if r.startswith("ok:"):
                phrases.append("Mo ti ṣe e")                           # Done
            elif r.startswith("warn:"):
                phrases.append("Mo gbiyanju, ṣugbọn ko ṣiṣẹ patapata")  # Tried, not fully done
            elif r.startswith("error:"):
                detail = r[6:]
                phrases.append(f"Aṣiṣe wa: {detail}")                  # Error occurred
            elif r.startswith("unknown:"):
                phrases.append("Emi ko ye ohun ti o fẹ, jọwọ sọ lẹẹkansi")  # Didn't understand
        return ". ".join(phrases) if phrases else "O ti ṣe"

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        print("=" * 52)
        print("🇳🇬  Àṣẹ — Yoruba Mac Agent (M1 Optimized, V2)")
        print("=" * 52)

        self.recorder.calibrate_noise_floor()
        self.speak("Ẹ káàbọ̀. Mo ṣetan.")
        print("\n⌨️  Press ENTER to speak | Ctrl+C to quit\n")

        consecutive_low_confidence = 0

        while True:
            try:
                input("[ ENTER to speak ] ")

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

                if not text:
                    self.speak("Emi ko gbọ rẹ. Jọwọ sọ lẹẹkansi.")
                    continue

                print(f"📝 [{confidence:.0%}] {text}")

                # 3. Confidence gate
                if confidence < CONFIDENCE_THRESHOLD:
                    self.speak("Jọwọ sọ lẹẹkansi, mi o gbọ o kedere")
                    consecutive_low_confidence += 1
                    if consecutive_low_confidence >= 3:
                        self.speak("Ṣe maikirofoonu ṣiṣẹ daradara?")
                        consecutive_low_confidence = 0
                    continue

                consecutive_low_confidence = 0

                # 4. Parse
                commands = self.parser.parse(stt_result)
                if not commands:
                    self.speak("Emi ko ye ohun ti o fẹ")
                    continue

                print(f"⚙️  {len(commands)} command(s): {commands}")

                # 5. Execute
                results = self.executor.execute_queue(commands)
                print(f"   results: {results}")

                # 6. Respond
                self.speak(self.results_to_yoruba(results))

            except KeyboardInterrupt:
                self.speak("O dabọ!")
                print("\nBye! 👋")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                self.speak("Aṣiṣe kan wa, jọwọ gbiyanju lẹẹkansi")


if __name__ == "__main__":
    YorubaAgent().run()
