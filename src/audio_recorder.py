"""
src/audio_recorder.py

Noise-calibrated audio recorder with VAD silence detection.
Handles: mic failures, audio clipping, background noise.
"""

import sounddevice as sd
import numpy as np
import sys

from config.settings import (
    SAMPLE_RATE,
    CHUNK_MS,
    SILENCE_SECONDS,
    MAX_RECORD_DURATION,
    MIN_NOISE_FLOOR,
    NOISE_CALIBRATION_SECS,
)


class AudioRecorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.noise_floor = MIN_NOISE_FLOOR
        self._verify_mic()

    def _verify_mic(self):
        """Check mic is accessible before the main loop starts."""
        try:
            test = sd.rec(
                int(0.1 * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            if float(np.max(np.abs(test))) == 0.0:
                print(
                    "⚠️  Microphone returned silence. Check System Settings → Privacy → Microphone.",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"❌ Microphone error: {e}", file=sys.stderr)
            print(
                "   Grant microphone permission to Terminal in System Settings → Privacy → Microphone",
                file=sys.stderr,
            )
            sys.exit(1)

    def calibrate_noise_floor(self, duration: float = NOISE_CALIBRATION_SECS):
        """
        Listen to ambient noise and set the detection threshold at 3× the RMS.
        Call once before the main loop — handles Lagos traffic, AC units, etc.
        """
        print("🎚️  Calibrating noise floor, please stay quiet...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        ambient_rms = float(np.sqrt(np.mean(audio**2)))
        # 3× ambient catches speech reliably while ignoring background hum
        self.noise_floor = max(ambient_rms * 3.0, MIN_NOISE_FLOOR)
        print(f"✅ Noise floor set to: {self.noise_floor:.4f}")

    def record_utterance(
        self,
        max_duration: float = MAX_RECORD_DURATION,
        silence_seconds: float = SILENCE_SECONDS,
    ) -> tuple[np.ndarray | None, bool]:
        """
        Record until natural pause. Returns (audio_array, was_clipped).
        Returns (None, False) if only silence was captured.

        Args:
            max_duration:    Maximum recording time in seconds.
            silence_seconds: Seconds of post-speech silence to stop recording.

        Returns:
            audio:       float32 numpy array at self.sample_rate, or None.
            was_clipped: True if signal hit near-maximum (distortion warning).
        """
        chunk_size = int(self.sample_rate * CHUNK_MS / 1000)
        required_silent = int(silence_seconds / (CHUNK_MS / 1000))
        max_chunks = int(max_duration / (CHUNK_MS / 1000))

        chunks: list[np.ndarray] = []
        silent_streak = 0
        has_speech = False

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_size)
                flat = chunk.flatten()
                chunks.append(flat.copy())
                rms = float(np.sqrt(np.mean(flat**2)))

                if rms > self.noise_floor:
                    has_speech = True
                    silent_streak = 0
                else:
                    silent_streak += 1

                # Stop only after speech has started and gone quiet
                if has_speech and silent_streak >= required_silent:
                    break

        if not has_speech:
            return None, False

        audio = np.concatenate(chunks)
        was_clipped = float(np.max(np.abs(audio))) > 0.95
        if was_clipped:
            print("⚠️  Audio clipped — try speaking a bit softer or moving back from mic")

        return audio, was_clipped
