"""
src/wake_word.py

Continuous Listening (Wake Word) engine using openWakeWord.
Provides background listening capabilities without triggering the heavy STT pipeline.
"""

import numpy as np

try:
    import openwakeword
    from openwakeword.model import Model
    openwakeword.utils.download_models()
except ImportError:
    Model = None

class WakeWordEngine:
    def __init__(self, threshold=0.5):
        self.threshold = threshold
        self.is_ready = False
        
        if Model is None:
            print("⚠️ openwakeword not installed. Continuous listening disabled.")
            return
            
        print("🎧 Initializing Wake Word Engine (openWakeWord)...")
        try:
            # Note: We use 'hey_jarvis' as a placeholder architecture proof.
            # A custom model for "Ẹ n lẹ Àṣẹ" needs to be trained using openWakeWord's utility.
            self.model = Model(wakeword_models=['hey_jarvis'], inference_framework="onnx")
            self.is_ready = True
            print("✅ Wake Word Engine ready. (Placeholder 'hey_jarvis' loaded, roadmap: train 'Ẹ n lẹ Àṣẹ')")
        except Exception as e:
            print(f"⚠️ Failed to load wake word model: {e}")

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Process a 16kHz audio chunk.
        Returns True if wake word is detected.
        """
        if not self.is_ready:
            return False
            
        # openWakeWord expects 16-bit PCM integer data
        if audio_chunk.dtype == np.float32:
            pcm_chunk = (audio_chunk * 32767).astype(np.int16)
        else:
            pcm_chunk = audio_chunk

        prediction = self.model.predict(pcm_chunk)
        
        for mdl_name, score in prediction.items():
            if score >= self.threshold:
                # Reset the internal state so it doesn't trigger repeatedly on the same audio
                self.model.reset()
                return True
                
        return False
