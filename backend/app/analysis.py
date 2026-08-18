import math
from pathlib import Path
import opensmile
import numpy as np

smile_lld = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.LowLevelDescriptors,
)

smile_func = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)

NOISE_LOUDNESS_THRESHOLD = 0.3
NOISE_JITTER_THRESHOLD = 0.001


def _extract_lld(audio_path: Path) -> dict:
    df = smile_lld.process_file(str(audio_path))

    def _series(col):
        vals = df[col].tolist()
        return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(v, 4) for v in vals]

    return {
        "F0": _series("F0semitoneFrom27.5Hz_sma3nz"),
        "Loudness": _series("Loudness_sma3"),
        "Jitter": _series("jitterLocal_sma3nz"),
    }


def _compute_confidence(audio_path: Path) -> tuple[float, str, str | None]:
    df = smile_func.process_file(str(audio_path))
    f = df.iloc[0]

    f0_std = float(f["F0semitoneFrom27.5Hz_sma3nz_stddevNorm"])
    jitter_mean = float(f["jitterLocal_sma3nz_amean"])
    loudness_std = float(f["loudness_sma3_stddevNorm"])

    score = 100 - (f0_std * 40 + jitter_mean * 1000 * 30 + loudness_std * 30)
    score = max(0, min(100, round(score, 1)))

    if score > 70:
        label = "Уверенно"
    elif score >= 40:
        label = "Средне"
    else:
        label = "Неуверенно"

    warning = None
    loudness_amean = float(f["loudness_sma3_amean"])
    if loudness_amean > NOISE_LOUDNESS_THRESHOLD or jitter_mean > NOISE_JITTER_THRESHOLD:
        warning = "Запись шумная даже после очистки, оценка может быть неточной"

    return score, label, warning


def analyze_session(session_id: str, session_dir: Path):
    from .sessions import get_session, set_results
    session = get_session(session_id)

    results = {
        "translations": [],
    }

    for tr in session["translations"]:
        lld = _extract_lld(tr["path"])
        score, label, warning = _compute_confidence(tr["path"])
        entry = {
            "id": tr["id"],
            "audio_url": f"/static/{session_id}/{tr['path'].name}",
            "duration_sec": round(tr["duration"], 2),
            "confidence_score": score,
            "confidence_label": label,
            "lld": lld,
        }
        if warning:
            entry["warning"] = warning
        results["translations"].append(entry)

    set_results(session_id, results)
