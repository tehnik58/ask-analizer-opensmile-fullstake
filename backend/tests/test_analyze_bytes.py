import io
import math
import struct
import wave

import pytest

from app.analysis import analyze_bytes


def _sine_wav_bytes(duration: float = 2.0, freq: float = 440.0, sr: int = 16000) -> bytes:
    n = int(sr * duration)
    samples = [int(1000 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{'h' * n}", *samples))
    return buf.getvalue()


def test_analyze_bytes_happy_path():
    result = analyze_bytes(_sine_wav_bytes(), "test.wav", audio_id="t1")
    assert result.id == "t1"
    assert abs(result.duration_sec - 2.0) < 0.05
    assert 0 <= result.confidence.score <= 100
    assert len(result.confidence.subscores) == 8
    assert set(result.lld) == {"F0", "Loudness", "Jitter"}
    assert len(result.lld["F0"]) > 0


def test_analyze_bytes_rejects_bad_extension():
    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        analyze_bytes(b"not audio", "song.txt")


def test_analyze_bytes_rejects_too_large():
    with pytest.raises(ValueError, match="большой"):
        analyze_bytes(b"x" * (20 * 1024 * 1024 + 1), "big.wav")
