"""
src/stt_engine.py

LyngualLabs/whisper-small-yoruba STT Engine.
Uses WhisperForConditionalGeneration directly (not the pipeline) to extract
real token-level confidence scores from the decoder's logprobs.
"""

import torch
import numpy as np
import re
from transformers import WhisperForConditionalGeneration, WhisperProcessor, GenerationConfig

from config.settings import (
    WHISPER_MODEL_ID,
    WHISPER_PRIMARY_LANGUAGE,
    SAMPLE_RATE,
)


class YorubaSTT:
    def __init__(self, model_id: str = WHISPER_MODEL_ID):
        self.model_id = model_id
        print(f"🔊 Loading STT Model ({model_id})...")

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.processor = WhisperProcessor.from_pretrained(model_id)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_id).to(self.device)

        # Configure generation to output scores and force Yoruba
        self.model.generation_config.language = WHISPER_PRIMARY_LANGUAGE
        self.model.generation_config.task = "transcribe"
        self.model.generation_config.output_scores = True
        self.model.generation_config.return_dict_in_generate = True

        print(f"✅ STT ready on {self.device}")

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
        """
        Transcribe a float32 audio array and return real confidence scores.

        Returns:
            dict with keys: text, language, confidence (0.0–1.0), is_code_switched
        """
        # Prepare input features (Whisper expects 16kHz mono)
        input_features = self.processor(
            audio_array,
            sampling_rate=sample_rate,
            return_tensors="pt",
        ).input_features.to(self.device)

        # Generate with score output so we can compute real confidence
        with torch.no_grad():
            outputs = self.model.generate(
                input_features,
                language=WHISPER_PRIMARY_LANGUAGE,
                task="transcribe",
                max_new_tokens=225,
            )

        # Decode text
        token_ids = outputs.sequences[0]
        text = self.processor.decode(token_ids, skip_special_tokens=True).strip()

        # Compute confidence from token log-probabilities
        confidence = self._compute_confidence(outputs)

        # Gate: Hallucination on noise → looping characters (å å å, మారిలి...).
        if self._is_hallucination(text):
            return {"text": "", "language": "yo", "confidence": 0.0, "is_code_switched": False}

        return {
            "text": text,
            "language": "yo",
            "confidence": confidence,
            "is_code_switched": self._detect_code_switching(text),
        }

    def _compute_confidence(self, outputs) -> float:
        """
        Compute a scalar confidence score (0.0–1.0) from the model's
        per-token generation scores.

        Strategy: For each generated token, softmax the logits and take the
        probability of the chosen token. Average these across all content
        tokens to get a single confidence value.
        """
        if not hasattr(outputs, 'scores') or not outputs.scores:
            return 0.5  # Fallback if scores weren't returned

        generated_ids = outputs.sequences[0]
        # scores is a tuple of (vocab_size,) tensors, one per generated step
        # generated_ids includes the decoder prompt; scores only cover generated steps
        num_prompt_tokens = generated_ids.shape[0] - len(outputs.scores)
        generated_token_ids = generated_ids[num_prompt_tokens:]

        eos_id = self.processor.tokenizer.eos_token_id
        vocab_size = self.processor.tokenizer.vocab_size

        token_probs = []
        for step_idx, logits in enumerate(outputs.scores):
            if step_idx >= len(generated_token_ids):
                break

            chosen_token_id = generated_token_ids[step_idx].item()

            # Skip special tokens (EOS, language tokens, timestamps, etc.)
            if chosen_token_id == eos_id:
                continue
            if chosen_token_id >= vocab_size:
                continue

            # Softmax → probability of chosen token
            probs = torch.nn.functional.softmax(logits[0].float(), dim=-1)
            token_probs.append(probs[chosen_token_id].item())

        if not token_probs:
            return 0.0

        # Average token probability as overall confidence
        avg_prob = sum(token_probs) / len(token_probs)

        # Clamp to [0.0, 1.0] for safety
        return max(0.0, min(1.0, avg_prob))

    def _is_hallucination(self, text: str) -> bool:
        """Detect Whisper hallucination patterns (repetitive noise transcription)."""
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
        """Heuristic to detect Yoruba-English code-switching."""
        yoruba_lookalikes = {
            "mo", "ni", "ti", "si", "fun", "ko", "o", "a", "wa", "se",
            "bi", "to", "lo", "ba", "le", "fi", "ma", "pa", "ran", "wo",
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        if not words:
            return False
        english_words = [w for w in words if w.lower() not in yoruba_lookalikes and len(w) > 2]
        return (len(english_words) / len(words)) > 0.3
