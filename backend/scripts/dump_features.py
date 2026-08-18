"""Диагностика: извлечение eGeMAPSv02 Functionals из всех аудио в папке."""
import sys
import math
from pathlib import Path
import opensmile
import numpy as np
import soundfile as sf

smile_func = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)

smile_lld = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
)

AUDIO_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Admin\Downloads\audio")
TARGET_SR = 16000

FEATURES = [
    ("F0 mean", "F0semitoneFrom27.5Hz_sma3nz_amean"),
    ("F0 stddevNorm", "F0semitoneFrom27.5Hz_sma3nz_stddevNorm"),
    ("Jitter amean", "jitterLocal_sma3nz_amean"),
    ("Shimmer amean", "shimmerLocaldB_sma3nz_amean"),
    ("HNR amean", "HNRdBACF_sma3nz_amean"),
    ("Loudness amean", "loudness_sma3_amean"),
    ("Loudness stddevNorm", "loudness_sma3_stddevNorm"),
    ("LoudnessPeaksPerSec", "loudnessPeaksPerSec"),
]


def _get_voiced_fraction(audio_path: Path) -> float:
    df = smile_lld.process_file(str(audio_path))
    f0_col = "F0semitoneFrom27.5Hz_sma3nz"
    total = len(df)
    voiced = df[f0_col].notna().sum()
    return round(voiced / total, 4) if total > 0 else 0.0


def analyze(audio_path: Path) -> dict:
    import tempfile, shutil
    tmp = Path(tempfile.mktemp(suffix=".wav"))
    audio, sr = sf.read(str(audio_path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        import librosa
        audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR
    sf.write(str(tmp), audio, sr, subtype="PCM_16")

    df = smile_func.process_file(str(tmp))
    f = df.iloc[0]

    result = {"file": audio_path.name, "duration": round(len(audio) / sr, 2)}
    for label, col in FEATURES:
        result[label] = round(float(f[col]), 6)
    result["VoicedFraction"] = _get_voiced_fraction(tmp)

    tmp.unlink()
    return result


if __name__ == "__main__":
    files = sorted(AUDIO_DIR.glob("*"))
    audio_files = [f for f in files if f.suffix.lower() in {".wav", ".mp3", ".ogg"}]
    if not audio_files:
        print(f"Нет аудио в {AUDIO_DIR}")
        sys.exit(1)

    print(f"{'Файл':<45} {'Dur':>5} ", end="")
    for label, _ in FEATURES:
        print(f" {label:>18}", end="")
    print(f" {'VoicedFrac':>10}")
    print("-" * 200)

    all_metrics = []
    for af in audio_files:
        r = analyze(af)
        all_metrics.append(r)
        print(f"{r['file']:<45} {r['duration']:>5.1f}", end="")
        for label, _ in FEATURES:
            print(f" {r[label]:>18.6f}", end="")
        print(f" {r['VoicedFraction']:>10.4f}")

    print("\n=== СТАТИСТИКА ===")
    for label, _ in FEATURES:
        vals = [r[label] for r in all_metrics]
        print(f"{label:<25} min={min(vals):.6f}  max={max(vals):.6f}  mean={np.mean(vals):.6f}  std={np.std(vals):.6f}")
    vfs = [r["VoicedFraction"] for r in all_metrics]
    print(f"{'VoicedFraction':<25} min={min(vfs):.4f}  max={max(vfs):.4f}  mean={np.mean(vfs):.4f}")
