import numpy as np
import soundfile as sf
from pathlib import Path
from app.denoise import denoise_file


def test_denoise_reduces_noise(tmp_path):
    sr = 16000
    duration = 2.0
    n = int(sr * duration)

    t = np.linspace(0, duration, n, dtype=np.float32)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    noise = 0.1 * np.random.randn(n).astype(np.float32)
    noisy = signal + noise

    wav_path = tmp_path / "noisy.wav"
    sf.write(str(wav_path), noisy, sr, subtype="PCM_16")

    audio_before, _ = sf.read(str(wav_path))
    rms_before = np.sqrt(np.mean(audio_before ** 2))

    denoise_file(wav_path)

    audio_after, sr_after = sf.read(str(wav_path))
    assert sr_after == sr
    assert len(audio_after) == len(audio_before)
    rms_after = np.sqrt(np.mean(audio_after ** 2))

    assert rms_after < rms_before


def test_denoise_preserves_silence(tmp_path):
    sr = 16000
    n = sr
    silence = np.zeros(n, dtype=np.float32)

    wav_path = tmp_path / "silence.wav"
    sf.write(str(wav_path), silence, sr, subtype="PCM_16")

    denoise_file(wav_path)

    audio, sr_out = sf.read(str(wav_path))
    assert sr_out == sr
    assert len(audio) == n
    assert np.max(np.abs(audio)) < 0.01
