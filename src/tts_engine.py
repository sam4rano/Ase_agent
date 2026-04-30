"""
src/tts_engine.py

Native Yoruba TTS using Meta's Massively Multilingual Speech (MMS) model.
Provides natural-sounding offline Yoruba voice.
Playback via macOS native 'afplay'.
"""

import torch
import os
import subprocess
import tempfile
import scipy.io.wavfile as wavfile
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
        """Generate and play Yoruba speech via afplay."""
        print(f"🔊 {text}")
        
        inputs = self.tokenizer(text, return_tensors="pt")
        
        with torch.no_grad():
            output = self.model(**inputs).waveform
            
        audio = output.numpy().flatten()
        
        # Save to temp file for afplay
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            wavfile.write(tmp_path, self.sample_rate, audio)
            
        try:
            # afplay is a built-in macOS command for audio playback
            subprocess.run(["afplay", tmp_path], check=True)
        except Exception as e:
            print(f"⚠️  Playback error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
