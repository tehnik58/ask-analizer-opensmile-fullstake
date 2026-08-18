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


def _compute_voiced_fraction(audio_path: Path) -> float:
    df = smile_lld.process_file(str(audio_path))
    f0_col = "F0semitoneFrom27.5Hz_sma3nz"
    total = len(df)
    voiced = df[f0_col].notna().sum()
    return round(voiced / total, 4) if total > 0 else 0.0


def analyze_session(session_id: str, session_dir: Path):
    from .sessions import get_session, set_results
    from .scoring import compute_confidence
    session = get_session(session_id)

    results = {
        "translations": [],
    }

    for tr in session["translations"]:
        lld = _extract_lld(tr["path"])

        df = smile_func.process_file(str(tr["path"]))
        features = df.iloc[0].to_dict()
        voiced_fraction = _compute_voiced_fraction(tr["path"])

        conf = compute_confidence(features, voiced_fraction)

        entry = {
            "id": tr["id"],
            "audio_url": f"/static/{session_id}/{tr['path'].name}",
            "duration_sec": round(tr["duration"], 2),
            "confidence_score": conf.score,
            "confidence_label": conf.label,
            "lld": lld,
            "metrics": {
                "hnr": conf.hnr_value,
                "subscores": [
                    {"name": s.name, "value": s.value, "score": s.score}
                    for s in conf.subscores
                ],
            },
        }
        if conf.is_noisy:
            entry["warning"] = "Запись шумная, оценка может быть неточной"

        results["translations"].append(entry)

    set_results(session_id, results)
