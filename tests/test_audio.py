"""
tests/test_audio.py — Unit tests for AudioRecorder.

Run: python3 -m pytest tests/test_audio.py -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

# Patch sounddevice before importing AudioRecorder to avoid hardware requirement
with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
    from src.audio_recorder import AudioRecorder


class TestAudioRecorder:

    def _make_recorder(self):
        """Create recorder with mic check bypassed."""
        with patch.object(AudioRecorder, "_verify_mic"):
            return AudioRecorder()

    def test_calibration_sets_noise_floor_above_minimum(self):
        recorder = self._make_recorder()
        # Simulate very quiet ambient noise (RMS ~ 0.001)
        fake_audio = np.zeros((24000, 1), dtype="float32") + 0.001
        with patch("sounddevice.rec", return_value=fake_audio), \
             patch("sounddevice.wait"):
            recorder.calibrate_noise_floor(duration=1.5)
        # floor = max(0.001 * 3, 0.008) = 0.008
        assert recorder.noise_floor >= 0.008

    def test_calibration_triples_ambient_rms(self):
        recorder = self._make_recorder()
        ambient = 0.05
        fake_audio = np.full((24000, 1), ambient, dtype="float32")
        with patch("sounddevice.rec", return_value=fake_audio), \
             patch("sounddevice.wait"):
            recorder.calibrate_noise_floor(duration=1.5)
        # floor should be ~3× ambient (within float tolerance)
        assert recorder.noise_floor == pytest.approx(ambient * 3.0, rel=0.01)

    def test_clipping_detected_when_near_max(self):
        recorder = self._make_recorder()
        recorder.noise_floor = 0.01
        loud_audio = np.full(4000, 0.98, dtype="float32")
        # Simulate: first chunk above noise floor, then silence
        silence = np.zeros(4000, dtype="float32")

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        # Alternate loud then silence chunks
        mock_stream.read.side_effect = [
            (loud_audio.reshape(-1, 1), None),
            *[(silence.reshape(-1, 1), None)] * 20,
        ]

        with patch("sounddevice.InputStream", return_value=mock_stream):
            audio, was_clipped = recorder.record_utterance()

        assert was_clipped is True

    def test_silence_only_returns_none(self):
        recorder = self._make_recorder()
        recorder.noise_floor = 0.02
        silence = np.zeros(4000, dtype="float32")

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.read.return_value = (silence.reshape(-1, 1), None)

        with patch("sounddevice.InputStream", return_value=mock_stream):
            audio, was_clipped = recorder.record_utterance()

        assert audio is None
        assert was_clipped is False
