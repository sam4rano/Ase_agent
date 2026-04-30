"""
src/tts_engine.py

Native Yoruba TTS using Meta's Massively Multilingual Speech (MMS) model.
Provides natural-sounding offline Yoruba voice.
"""

import torch
import sounddevice as sd
from transformers import VitsModel, AutoTokenizer
from config.settings import TTS_MODEL_ID

class YorubaTTS:
    def __init__(self, model_id: str = TTS_MODEL_ID):
        print(f"🔊 Loading Yoruba TTS ({model_id.split('/')[-1]})...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = VitsModel.from_pretrained(model_id)
        self.sample_rate = self.model.config.sampling_rate
        print("✅ TTS ready")

    def speak(self, text: str):
        """Generate and play Yoruba speech synchronously."""
        print(f"🔊 {text}")
        
        # The model is sensitive to English punctuation, clean it up slightly if needed,
        # but basic punctuation is fine.
        inputs = self.tokenizer(text, return_tensors="pt")
        
        with torch.no_grad():
            output = self.model(**inputs).waveform
            
        audio = output.numpy().flatten()
        sd.play(audio, samplerate=self.sample_rate)
        sd.wait()
