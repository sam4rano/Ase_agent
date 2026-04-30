"""
src/stt_engine.py

MLX Whisper STT — auto-detects language (English, Yoruba, mixed).
Filters hallucinations before returning text.
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
)


class YorubaSTT:
    def __init__(self, model_id: str = WHISPER_MODEL_ID):
        self.model_id = model_id
        lang_label = WHISPER_PRIMARY_LANGUAGE or "auto-detect"
        print(f"🔊 Whisper ready ({model_id.split('/')[-1]}, language={lang_label})")

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Transcribe a float32 audio array.

        Returns:
            {
                "text": str,
                "language": str,
                "confidence": float (0-1),
                "is_code_switched": bool,
            }
        """
        tmp_path = self._write_wav(audio_array, sample_rate)
        try:
            return self._run(tmp_path)
        finally:
            os.unlink(tmp_path)

    # ── Internal ──────────────────────────────────────────────────────────

    def _write_wav(self, audio: np.ndarray, sample_rate: int) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        return path

    def _run(self, wav_path: str) -> dict:
        _empty = {"text": "", "language": "en", "confidence": 0.0, "is_code_switched": False}

        result = mlx_whisper.transcribe(
            wav_path,
            path_or_hf_repo=self.model_id,
            language=WHISPER_PRIMARY_LANGUAGE,  # None = auto-detect (English, Yoruba, mixed)
            word_timestamps=True,
            fp16=True,
        )

        text = result["text"].strip()
        confidence = self._estimate_confidence(result)
        language = result.get("language", "en")

        # Gate 1: Whisper says there was no speech — trust it.
        if self._avg_no_speech_prob(result) > 0.6:
            return _empty

        # Gate 2: Hallucination on noise → looping characters (å å å, మారిలి...).
        if self._is_hallucination(text):
            return _empty

        return {
            "text": text,
            "language": language,
            "confidence": confidence,
            "is_code_switched": self._detect_code_switching(text),
        }

    def _avg_no_speech_prob(self, result: dict) -> float:
        segments = result.get("segments", [])
        if not segments:
            return 1.0
        return float(np.mean([s.get("no_speech_prob", 0.0) for s in segments]))

    def _is_hallucination(self, text: str) -> bool:
        """
        Detect repeated-token or repeated-character hallucination patterns.
        Examples: "å å å å å å å å", "మారిలిలిలిలిలిలి...", "... ... ... ..."
        """
        if not text or not text.strip():
            return True

        tokens = text.split()
        if len(tokens) >= 8:
            most_common = max(set(tokens), key=tokens.count)
            if tokens.count(most_common) / len(tokens) > 0.6:
                return True

        chars = [c for c in text if not c.isspace()]
        if len(chars) > 10:
            most_common_char = max(set(chars), key=chars.count)
            if chars.count(most_common_char) / len(chars) > 0.7:
                return True

        return False

    def _estimate_confidence(self, result: dict) -> float:
        """avg_logprob: 0 is perfect, -1.5 is very poor. Map to 0-1."""
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        avg_logprob = float(np.mean([s.get("avg_logprob", -1.5) for s in segments]))
        return float(np.clip(1.0 + avg_logprob / 1.5, 0.0, 1.0))

    def _detect_code_switching(self, text: str) -> bool:
        """True if >30% of words look like English mixed into non-English speech."""
        yoruba_lookalikes = {
            "mo", "ni", "ti", "si", "fun", "ko", "o", "a", "wa", "se",
            "bi", "to", "lo", "ba", "le", "fi", "ma", "pa", "ran", "wo",
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        if not words:
            return False
        english_words = [w for w in words if w.lower() not in yoruba_lookalikes and len(w) > 2]
        return (len(english_words) / len(words)) > 0.3
