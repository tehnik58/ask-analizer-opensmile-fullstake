import io
import struct
import wave
import math
from pathlib import Path
from app.analysis import _extract_lld, _compute_confidence


def _make_wav(path: Path, duration: float = 2.0, freq: float = 440.0, sr: int = 16000):
    n = int(sr * duration)
    samples = [int(1000 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)]
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{'h' * n}", *samples))


def test_extract_lld(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav)
    lld = _extract_lld(wav)
    assert "F0" in lld
    assert "Loudness" in lld
    assert "Jitter" in lld
    assert len(lld["F0"]) > 0
    assert len(lld["Loudness"]) > 0
    assert len(lld["Jitter"]) > 0
    assert all(v is None or isinstance(v, (int, float)) for v in lld["F0"])


def test_compute_confidence(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav)
    score, label, warning = _compute_confidence(wav)
    assert 0 <= score <= 100
    assert label in ("Уверенно", "Средне", "Неуверенно")


def test_silence_nan_handling(tmp_path):
    wav = tmp_path / "silence.wav"
    n = 16000
    with wave.open(str(wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack(f"<{'h' * n}", *([0] * n)))
    lld = _extract_lld(wav)
    assert len(lld["F0"]) > 0
    assert all(v is None or isinstance(v, (int, float)) for v in lld["F0"])
