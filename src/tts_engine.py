"""
src/tts_engine.py

Native Yoruba TTS using F5-TTS Zero-Shot Voice Cloning model.
Provides the most natural-sounding offline Yoruba voice with full tonal diacritic support.
Playback via macOS native 'afplay'.
"""

import os
import subprocess
from huggingface_hub import hf_hub_download

# CRITICAL: Must bypass pinyin conversion BEFORE any other F5-TTS import
import f5_tts.model.utils as f5_utils
f5_utils.convert_char_to_pinyin = lambda texts, polyphone=True: texts

from f5_tts.api import F5TTS

class YorubaTTS:
    def __init__(self):
        print("🔊 Downloading/Loading F5-TTS Yoruba model (~1.35GB)...")
        self.ckpt = hf_hub_download("naijaml/f5-tts-yoruba", "model_150000.pt")
        self.vocab = hf_hub_download("naijaml/f5-tts-yoruba", "vocab.txt")
        self.ref_wav = hf_hub_download("naijaml/f5-tts-yoruba", "samples/female_1_greeting.wav")
        self.ref_text = "ẹ kú àárọ̀, báwo ni àwọn ọmọ yín ṣe wà?"
        
        self.f5tts = F5TTS(
            model="F5TTS_v1_Base",
            ckpt_file=self.ckpt,
            vocab_file=self.vocab,
            device="mps", # Optimized for Apple Silicon
        )
        print("✅ F5-TTS ready")

    def speak(self, text: str):
        """Generate and play Yoruba speech via F5-TTS and afplay."""
        print(f"🔊 {text}")
        
        output_wav = "f5_tts_output.wav"
        
        try:
            wav, sr, _ = self.f5tts.infer(
                ref_file=self.ref_wav,
                ref_text=self.ref_text,
                gen_text=text,
                speed=1.0,
                nfe_step=16,
                file_wave=output_wav,
            )
            
            # Play audio using macOS native afplay
            subprocess.run(["afplay", output_wav], check=True)
        except Exception as e:
            print(f"⚠️  Playback error: {e}")
        finally:
            if os.path.exists(output_wav):
                os.remove(output_wav)
