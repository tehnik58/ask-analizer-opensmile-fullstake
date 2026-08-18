import math
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import opensmile
import numpy as np

from .scoring import compute_confidence, ConfidenceResult
from .audio import convert_url_to_wav
from .denoise import denoise_file

smile_lld = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
)

smile_func = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)


@dataclass
class AudioResult:
    id: str
    audio_url: str
    duration_sec: float
    confidence: ConfidenceResult
    lld: dict = field(default_factory=dict)


def extract_lld(audio_path: Path) -> dict:
    """Extract low-level descriptors (F0, Loudness, Jitter) for graph visualization."""
    df = smile_lld.process_file(str(audio_path))

    def _series(col):
        vals = df[col].tolist()
        return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(v, 4) for v in vals]

    return {
        "F0": _series("F0semitoneFrom27.5Hz_sma3nz"),
        "Loudness": _series("Loudness_sma3"),
        "Jitter": _series("jitterLocal_sma3nz"),
    }


def compute_voiced_fraction(audio_path: Path) -> float:
    """Fraction of frames with voiced speech (F0 detected)."""
    df = smile_lld.process_file(str(audio_path))
    f0_col = "F0semitoneFrom27.5Hz_sma3nz"
    total = len(df)
    voiced = df[f0_col].notna().sum()
    return round(voiced / total, 4) if total > 0 else 0.0


def compute_rhythm_cv(audio_path: Path) -> float:
    """CV of segment durations between loudness onsets. High CV = uneven rhythm."""
    df = smile_lld.process_file(str(audio_path))
    loud = df["Loudness_sma3"].to_numpy()
    if len(loud) < 10:
        return 0.5
    threshold = np.percentile(loud, 75)
    active = loud > threshold
    changes = np.diff(active.astype(int))
    onsets = np.where(changes == 1)[0]
    if len(onsets) < 5:
        return 0.5
    seg_lens = np.diff(onsets).astype(float)
    mean_len = np.mean(seg_lens)
    if mean_len == 0:
        return 0.5
    return float(np.std(seg_lens) / mean_len)


def analyze_translations(translations):
    """
    Analyze a list of audio translations from URLs.

    Args:
        translations: list of dicts, each with:
            - id (str): unique identifier
            - url (str): audio URL (http://, https://, file:///)

    Returns:
        list[AudioResult]: analysis results with confidence scores and LLD data.
        Temp files are cleaned up automatically.
    """
    results = []
    tmp_files = []
    try:
        for tr in translations:
            raw_path, duration = convert_url_to_wav(tr["url"])
            tmp_files.append(raw_path)

            denoised_path = Path(tempfile.mktemp(suffix=".wav"))
            tmp_files.append(denoised_path)
            shutil.copy2(raw_path, denoised_path)
            denoise_file(denoised_path)

            lld = extract_lld(denoised_path)
            df = smile_func.process_file(str(raw_path))
            features = df.iloc[0].to_dict()
            voiced_fraction = compute_voiced_fraction(raw_path)
            rhythm_cv = compute_rhythm_cv(raw_path)
            conf = compute_confidence(features, voiced_fraction, rhythm_cv)

            results.append(AudioResult(
                id=tr["id"],
                audio_url=tr["url"],
                duration_sec=round(duration, 2),
                confidence=conf,
                lld=lld,
            ))
    finally:
        for f in tmp_files:
            f.unlink(missing_ok=True)
    return results
