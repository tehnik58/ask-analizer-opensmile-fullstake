import io
import struct
import wave
import math
from pathlib import Path
from app.analysis import _extract_lld, _compute_voiced_fraction
from app.scoring import compute_confidence, _subscore
import opensmile


def _make_wav(path: Path, duration: float = 2.0, freq: float = 440.0, sr: int = 16000):
    n = int(sr * duration)
    samples = [int(1000 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)]
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{'h' * n}", *samples))


smile_func = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)


def _get_features(audio_path):
    df = smile_func.process_file(str(audio_path))
    return df.iloc[0].to_dict()


# --- Unit-тесты для _subscore ---

def test_subscore_at_good():
    assert _subscore(value=5.5, good=5.5, bad=2.0, invert=False) == 100.0


def test_subscore_at_bad():
    assert _subscore(value=2.0, good=5.5, bad=2.0, invert=False) == 0.0


def test_subscore_midpoint():
    score = _subscore(value=3.75, good=5.5, bad=2.0, invert=False)
    assert 49.0 <= score <= 51.0


def test_subscore_invert():
    assert _subscore(value=0.025, good=0.025, bad=0.055, invert=True) == 100.0
    assert _subscore(value=0.055, good=0.025, bad=0.055, invert=True) == 0.0


def test_subscore_clamp():
    assert _subscore(value=1.0, good=5.5, bad=2.0, invert=False) == 0.0
    assert _subscore(value=10.0, good=5.5, bad=2.0, invert=False) == 100.0


# --- Интеграционные тесты ---

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
    features = _get_features(wav)
    vf = _compute_voiced_fraction(wav)
    result = compute_confidence(features, vf)
    assert 0 <= result.score <= 100
    assert result.label in ("Уверенно", "Средне", "Неуверенно")
    assert len(result.subscores) == 5
    assert all(0 <= s.score <= 100 for s in result.subscores)


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


def test_confident_better_than_noisy(tmp_path):
    import numpy as np
    import soundfile as sf
    sr = 16000
    n = sr * 2
    t = np.linspace(0, 2, n, dtype=np.float32)

    clean = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    clean_path = tmp_path / "clean.wav"
    sf.write(str(clean_path), clean, sr, subtype="PCM_16")

    noise = 0.3 * np.random.randn(n).astype(np.float32)
    tremolo = 1 + 0.5 * np.sin(2 * np.pi * 5 * t)
    noisy = (0.3 * np.sin(2 * np.pi * 80 * t) * tremolo + noise).astype(np.float32)
    noisy_path = tmp_path / "noisy.wav"
    sf.write(str(noisy_path), noisy, sr, subtype="PCM_16")

    feat_clean = _get_features(clean_path)
    vf_clean = _compute_voiced_fraction(clean_path)
    res_clean = compute_confidence(feat_clean, vf_clean)

    feat_noisy = _get_features(noisy_path)
    vf_noisy = _compute_voiced_fraction(noisy_path)
    res_noisy = compute_confidence(feat_noisy, vf_noisy)

    assert res_clean.score > res_noisy.score, f"clean={res_clean.score} should be > noisy={res_noisy.score}"


# --- Регрессионный тест: профили реальных записей ---

def test_real_recordings_profiles():
    """Проверяет скоринг на фиксированных features из реальных записей."""
    # ogg — уверенный голос
    ogg_features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.1997,
        "jitterLocal_sma3nz_amean": 0.0261,
        "HNRdBACF_sma3nz_amean": 4.733,
        "loudnessPeaksPerSec": 4.0,
    }
    ogg = compute_confidence(ogg_features, voiced_fraction=1.0)
    assert ogg.score >= 80.0, f"ogg score {ogg.score} < 80"
    assert ogg.label == "Уверенно"

    # Record.mp3 — уверенный голос
    record_features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.2698,
        "jitterLocal_sma3nz_amean": 0.0237,
        "HNRdBACF_sma3nz_amean": 4.121,
        "loudnessPeaksPerSec": 2.64,
    }
    record = compute_confidence(record_features, voiced_fraction=1.0)
    assert record.score >= 80.0, f"Record score {record.score} < 80"
    assert record.label == "Уверенно"

    # Record(1).mp3 — уверенный, но тараторящий → ниже двух других
    rush_features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.3119,
        "jitterLocal_sma3nz_amean": 0.0388,
        "HNRdBACF_sma3nz_amean": 3.521,
        "loudnessPeaksPerSec": 2.16,
    }
    rush = compute_confidence(rush_features, voiced_fraction=1.0)
    assert rush.score < record.score, f"rush={rush.score} should be < record={record.score}"
    assert rush.score < ogg.score, f"rush={rush.score} should be < ogg={ogg.score}"
    assert rush.label in ("Уверенно", "Средне")
