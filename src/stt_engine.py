"""
src/stt_engine.py

MLX Whisper STT with Yoruba-first transcription and confidence gating.
Handles: low confidence, code-switching detection, temp file cleanup.
"""

import mlx_whisper
import numpy as np
import tempfile
import wave
import os
import re

from config.settings import (
    WHISPER_MODEL_ID,
    WHISPER_PRIMARY_LANGUAGE,
    CONFIDENCE_FALLBACK,
)


class YorubaSTT:
    def __init__(self, model_id: str = WHISPER_MODEL_ID):
        self.model_id = model_id
        print(f"🔊 Whisper ready ({model_id.split('/')[-1]})")

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Transcribe a float32 audio array.

        Returns:
            {
                "text": str,
                "language": str,
                "confidence": float (0–1),
                "is_code_switched": bool,
            }
        """
        tmp_path = self._write_wav(audio_array, sample_rate)
        try:
            return self._run(tmp_path)
        finally:
            os.unlink(tmp_path)  # always clean up the temp file

    # ── Internal ──────────────────────────────────────────────────────────

    def _write_wav(self, audio: np.ndarray, sample_rate: int) -> str:
        """Write float32 array to a temporary WAV file. Returns the path."""
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        return path

    def _run(self, wav_path: str) -> dict:
        """Run Whisper twice if needed (Yoruba-first, then auto-detect fallback)."""
        # Primary: force Yoruba
        result_yo = mlx_whisper.transcribe(
            wav_path,
            path_or_hf_repo=self.model_id,
            language=WHISPER_PRIMARY_LANGUAGE,
            word_timestamps=True,
            fp16=True,
        )
        text_yo = result_yo["text"].strip()
        confidence = self._estimate_confidence(result_yo)

        text = text_yo
        language = result_yo.get("language", WHISPER_PRIMARY_LANGUAGE)

        # Fallback: if low confidence, try auto-detect
        if confidence < CONFIDENCE_FALLBACK:
            result_auto = mlx_whisper.transcribe(
                wav_path,
                path_or_hf_repo=self.model_id,
                language=None,
                fp16=True,
            )
            auto_text = result_auto["text"].strip()
            if len(auto_text) > len(text_yo):
                text = auto_text
                language = result_auto.get("language", "auto")
                print(f"ℹ️  Low confidence ({confidence:.0%}), switched to auto-detect")

        return {
            "text": text,
            "language": language,
            "confidence": confidence,
            "is_code_switched": self._detect_code_switching(text),
        }

    def _estimate_confidence(self, result: dict) -> float:
        """
        Map Whisper's avg_logprob (−∞ to 0) to a 0–1 confidence score.
        −0.2 ≈ 0.87 (good), −1.0 ≈ 0.33 (poor), −1.5 ≈ 0.0 (very poor).
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        avg_logprob = float(np.mean([s.get("avg_logprob", -1.5) for s in segments]))
        return float(np.clip(1.0 + avg_logprob / 1.5, 0.0, 1.0))

    def _detect_code_switching(self, text: str) -> bool:
        """
        Flag text as code-switched when >30% of words appear to be English.
        Yoruba words that look like English are excluded from the count.
        """
        # Yoruba function words that could be mistaken for English
        yoruba_lookalikes = {
            "mo", "ni", "ti", "si", "fun", "ko", "o", "a", "wa", "se",
            "bi", "to", "lo", "ba", "le", "fi", "ma", "pa", "ran", "wo",
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        if not words:
            return False
        english_words = [
            w for w in words
            if w.lower() not in yoruba_lookalikes and len(w) > 2
        ]
        return (len(english_words) / len(words)) > 0.3
