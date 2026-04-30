"""
src/stt_engine.py

NCAIR1/Yoruba-ASR STT Engine.
Uses transformers to load the fine-tuned Yoruba Whisper model.
"""

import torch
import numpy as np
import tempfile
import wave
import os
import re
from transformers import pipeline

from config.settings import (
    WHISPER_MODEL_ID,
    WHISPER_PRIMARY_LANGUAGE,
)

class YorubaSTT:
    def __init__(self, model_id: str = WHISPER_MODEL_ID):
        self.model_id = model_id
        print(f"🔊 Loading STT Model ({model_id})...")
        
        # Use transformers pipeline for STT
        # We use CPU or MPS if available. Standard transformers on Mac works well with MPS.
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            chunk_length_s=30,
            device=device,
        )
        print(f"✅ STT ready on {device}")

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Transcribe a float32 audio array.
        """
        # NCAIR1 model expects 16kHz
        # audio_array is already 16kHz from AudioRecorder
        
        result = self.pipe(
            audio_array,
            generate_kwargs={"language": WHISPER_PRIMARY_LANGUAGE},
            return_timestamps=False,
        )

        text = result["text"].strip()
        # transformers pipeline doesn't give logprobs as easily as mlx-whisper in one call,
        # but for fine-tuned models on their target language, confidence is usually high.
        # We'll set a placeholder or implement score extraction if needed.
        confidence = 0.9 if text else 0.0 

        # Gate 2: Hallucination on noise → looping characters (å å å, మారిలి...).
        if self._is_hallucination(text):
            return {"text": "", "language": "yo", "confidence": 0.0, "is_code_switched": False}

        return {
            "text": text,
            "language": "yo",
            "confidence": confidence,
            "is_code_switched": self._detect_code_switching(text),
        }

    def _is_hallucination(self, text: str) -> bool:
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

    def _detect_code_switching(self, text: str) -> bool:
        yoruba_lookalikes = {
            "mo", "ni", "ti", "si", "fun", "ko", "o", "a", "wa", "se",
            "bi", "to", "lo", "ba", "le", "fi", "ma", "pa", "ran", "wo",
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        if not words:
            return False
        english_words = [w for w in words if w.lower() not in yoruba_lookalikes and len(w) > 2]
        return (len(english_words) / len(words)) > 0.3
