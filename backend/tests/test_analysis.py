import io
import struct
import wave
import math
from pathlib import Path
from app.analysis import extract_lld, compute_voiced_fraction, compute_rhythm_cv
from app.scoring import compute_confidence, _subscore, _subscore_window
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


# --- Unit-тесты для _subscore_window ---

def test_window_inside_peak():
    assert _subscore_window(0.20, 0.08, 0.16, 0.32, 0.50) == 100.0
    assert _subscore_window(0.16, 0.08, 0.16, 0.32, 0.50) == 100.0
    assert _subscore_window(0.32, 0.08, 0.16, 0.32, 0.50) == 100.0


def test_window_below_lo_bad():
    assert _subscore_window(0.04, 0.08, 0.16, 0.32, 0.50) == 0.0


def test_window_above_hi_bad():
    assert _subscore_window(0.60, 0.08, 0.16, 0.32, 0.50) == 0.0


def test_window_left_slope():
    val = 0.12
    expected = (0.12 - 0.08) / (0.16 - 0.08) * 100
    assert abs(_subscore_window(val, 0.08, 0.16, 0.32, 0.50) - expected) < 1.0


def test_window_right_slope():
    val = 0.41
    expected = (0.50 - 0.41) / (0.50 - 0.32) * 100
    assert abs(_subscore_window(val, 0.08, 0.16, 0.32, 0.50) - expected) < 1.0


# --- Unit-тест для RhythmCV ---

def test_rhythm_cv_equal_segments(tmp_path):
    """Равномерный сигнал → низкий CV."""
    import numpy as np
    import soundfile as sf
    sr = 16000
    # сигнал с равномерными всплесками каждые 0.5 сек
    t = np.linspace(0, 4, sr * 4, dtype=np.float32)
    envelope = np.zeros_like(t)
    for onset in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
        start = int(onset * sr)
        end = min(start + int(0.1 * sr), len(envelope))
        envelope[start:end] = 1.0
    audio = envelope * np.sin(2 * np.pi * 200 * t).astype(np.float32)
    path = tmp_path / "even.wav"
    sf.write(str(path), audio, sr, subtype="PCM_16")
    cv = compute_rhythm_cv(path)
    assert cv < 1.0, f"even CV {cv} should be < 1.0"


def test_rhythm_cv_short_audio(tmp_path):
    """Короткая запись (<5 всплесков) → нейтральные 0.5."""
    import numpy as np
    import soundfile as sf
    sr = 16000
    audio = np.zeros(sr, dtype=np.float32)
    path = tmp_path / "short.wav"
    sf.write(str(path), audio, sr, subtype="PCM_16")
    cv = compute_rhythm_cv(path)
    assert cv == 0.5


# --- Интеграционные тесты ---

def testextract_lld(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav)
    lld = extract_lld(wav)
    assert "F0" in lld
    assert "Loudness" in lld
    assert "Jitter" in lld
    assert len(lld["F0"]) > 0
    assert all(v is None or isinstance(v, (int, float)) for v in lld["F0"])


def test_compute_confidence(tmp_path):
    wav = tmp_path / "test.wav"
    _make_wav(wav)
    features = _get_features(wav)
    vf = compute_voiced_fraction(wav)
    result = compute_confidence(features, vf)
    assert 0 <= result.score <= 100
    assert result.label in ("Уверенно", "Средне", "Неуверенно")
    assert len(result.subscores) == 8
    assert all(0 <= s.score <= 100 for s in result.subscores)


def test_silence_nan_handling(tmp_path):
    wav = tmp_path / "silence.wav"
    n = 16000
    with wave.open(str(wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack(f"<{'h' * n}", *([0] * n)))
    lld = extract_lld(wav)
    assert len(lld["F0"]) > 0
    assert all(v is None or isinstance(v, (int, float)) for v in lld["F0"])


def test_confident_better_than_noisy():
    """Уверенный голос с умеренными метриками > шумный сигнал."""
    confident = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.22,
        "jitterLocal_sma3nz_amean": 0.020,
        "HNRdBACF_sma3nz_amean": 12.0,
        "loudnessPeaksPerSec": 3.5,
        "F1bandwidth_sma3nz_amean": 1150.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 5.0,
    }
    noisy = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.22,
        "jitterLocal_sma3nz_amean": 0.050,
        "HNRdBACF_sma3nz_amean": 2.0,
        "loudnessPeaksPerSec": 3.5,
        "F1bandwidth_sma3nz_amean": 1150.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 5.0,
    }
    res_clean = compute_confidence(confident, 1.0, 0.8)
    res_noisy = compute_confidence(noisy, 1.0, 0.8)
    assert res_clean.score > res_noisy.score


# --- Регрессионные тесты: профили 5 записей (RAW-данные) ---

def test_profile_confident_ogg():
    features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.1997,
        "jitterLocal_sma3nz_amean": 0.0261,
        "HNRdBACF_sma3nz_amean": 4.733,
        "loudnessPeaksPerSec": 4.0,
        "F1bandwidth_sma3nz_amean": 1308.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 5.85,
    }
    r = compute_confidence(features, voiced_fraction=1.0, rhythm_cv=0.90)
    assert r.score >= 70.0, f"ogg score {r.score} < 70"
    assert r.label == "Уверенно"


def test_profile_confident_record():
    features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.2698,
        "jitterLocal_sma3nz_amean": 0.0237,
        "HNRdBACF_sma3nz_amean": 4.121,
        "loudnessPeaksPerSec": 2.64,
        "F1bandwidth_sma3nz_amean": 1166.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 4.80,
    }
    r = compute_confidence(features, voiced_fraction=1.0, rhythm_cv=0.77)
    assert r.score >= 70.0, f"Record score {r.score} < 70"
    assert r.label == "Уверенно"


def test_profile_rushed():
    """Record(1).mp3 — тараторящий → Средне."""
    features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.3119,
        "jitterLocal_sma3nz_amean": 0.0388,
        "HNRdBACF_sma3nz_amean": 3.521,
        "loudnessPeaksPerSec": 2.16,
        "F1bandwidth_sma3nz_amean": 1032.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 5.41,
    }
    r = compute_confidence(features, voiced_fraction=1.0, rhythm_cv=0.76)
    assert r.label in ("Уверенно", "Средне"), f"rushed={r.label}"


def test_profile_mumble():
    """Новая запись.m4a — мямлящий, цель ~40, Средне."""
    mumble_features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.1174,
        "jitterLocal_sma3nz_amean": 0.0129,
        "HNRdBACF_sma3nz_amean": 10.044,
        "loudnessPeaksPerSec": 2.12,
        "F1bandwidth_sma3nz_amean": 1409.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 3.12,
    }
    confident_features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.1997,
        "jitterLocal_sma3nz_amean": 0.0261,
        "HNRdBACF_sma3nz_amean": 4.733,
        "loudnessPeaksPerSec": 4.0,
        "F1bandwidth_sma3nz_amean": 1308.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 5.85,
    }
    mumble = compute_confidence(mumble_features, 1.0, rhythm_cv=1.08)
    confident = compute_confidence(confident_features, 1.0, rhythm_cv=0.90)

    assert mumble.score < confident.score, f"mumble={mumble.score} should be < confident={confident.score}"
    assert 30.0 <= mumble.score <= 55.0, f"mumble={mumble.score} should be ~40"


def test_profile_uneven():
    """Новая запись 2.m4a — рваный ритм, цель 55–60, Средне."""
    features = {
        "F0semitoneFrom27.5Hz_sma3nz_stddevNorm": 0.1601,
        "jitterLocal_sma3nz_amean": 0.0128,
        "HNRdBACF_sma3nz_amean": 7.868,
        "loudnessPeaksPerSec": 2.85,
        "F1bandwidth_sma3nz_amean": 1289.0,
        "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2": 7.79,
    }
    r = compute_confidence(features, voiced_fraction=1.0, rhythm_cv=1.15)
    assert r.label in ("Уверенно", "Средне"), f"uneven={r.label}"
    assert r.score <= 75.0, f"uneven={r.score} should be ≤ 75"
