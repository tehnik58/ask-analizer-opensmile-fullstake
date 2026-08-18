"""
Модуль скоринга уверенности речи.

8 суб-скоров 0–100. F0Std — U-образная шкала.
Метрики артикуляции/ритма вычисляются по RAW-аудио (denoise искажает просодию).
"""

from dataclasses import dataclass


@dataclass
class SubScore:
    name: str
    value: float
    score: float


@dataclass
class ConfidenceResult:
    score: float
    label: str
    subscores: list[SubScore]
    hnr_value: float
    is_noisy: bool


def _subscore(value: float, good: float, bad: float, invert: bool) -> float:
    """Линейная интерполяция 0–100 с clamp."""
    if invert:
        if value <= good:
            return 100.0
        if value >= bad:
            return 0.0
        return max(0.0, min(100.0, (bad - value) / (bad - good) * 100))
    else:
        if value >= good:
            return 100.0
        if value <= bad:
            return 0.0
        return max(0.0, min(100.0, (value - bad) / (good - bad) * 100))


def _subscore_window(
    value: float, lo_bad: float, lo_good: float, hi_good: float, hi_bad: float
) -> float:
    """U-образная шкала: 100 в окне [lo_good, hi_good], падение к 0 за [lo_bad, hi_bad]."""
    if lo_good <= value <= hi_good:
        return 100.0
    if value < lo_bad or value > hi_bad:
        return 0.0
    if value < lo_good:
        return max(0.0, min(100.0, (value - lo_bad) / (lo_good - lo_bad) * 100))
    return max(0.0, min(100.0, (hi_bad - value) / (hi_bad - hi_good) * 100))


METRIC_DEFS = {
    "F0Std": {
        "name": "F0 вариативность",
        "feature": "F0semitoneFrom27.5Hz_sma3nz_stddevNorm",
        "kind": "window",
        "lo_bad": 0.08, "lo_good": 0.16, "hi_good": 0.32, "hi_bad": 0.50,
        "weight": 0.20,
    },
    "Jitter": {
        "name": "Jitter (дрожание)",
        "feature": "jitterLocal_sma3nz_amean",
        "kind": "linear",
        "good": 0.025, "bad": 0.055, "invert": True,
        "weight": 0.10,
    },
    "HNR": {
        "name": "HNR (гармоничность)",
        "feature": "HNRdBACF_sma3nz_amean",
        "kind": "linear",
        "good": 5.5, "bad": 2.0, "invert": False,
        "weight": 0.05,
    },
    "VoicedFraction": {
        "name": "Доля речи",
        "feature": None,
        "kind": "linear",
        "good": 0.80, "bad": 0.40, "invert": False,
        "weight": 0.05,
    },
    "Tempo": {
        "name": "Темп речи",
        "feature": "loudnessPeaksPerSec",
        "kind": "linear",
        "good": 3.5, "bad": 2.0, "invert": False,
        "weight": 0.15,
    },
    "F1bandwidth": {
        "name": "Артикуляция",
        "feature": "F1bandwidth_sma3nz_amean",
        "kind": "linear",
        "good": 1100.0, "bad": 1450.0, "invert": True,
        "weight": 0.10,
    },
    "F0Range": {
        "name": "Диапазон тона",
        "feature": "F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2",
        "kind": "linear",
        "good": 5.5, "bad": 2.5, "invert": False,
        "weight": 0.15,
    },
    "RhythmCV": {
        "name": "Ритм",
        "feature": None,
        "kind": "linear",
        "good": 0.82, "bad": 1.12, "invert": True,
        "weight": 0.20,
    },
}

NOISE_HNR_THRESHOLD = 10.0


def compute_confidence(features: dict, voiced_fraction: float, rhythm_cv: float = 0.5) -> ConfidenceResult:
    subscores = []
    weighted_sum = 0.0
    total_weight = 0.0

    for key, defn in METRIC_DEFS.items():
        if key == "RhythmCV":
            value = rhythm_cv
        elif defn["feature"] is not None:
            value = features.get(defn["feature"], 0.0)
        else:
            value = voiced_fraction

        if defn["kind"] == "window":
            score = _subscore_window(
                float(value), defn["lo_bad"], defn["lo_good"], defn["hi_good"], defn["hi_bad"]
            )
        else:
            score = _subscore(float(value), defn["good"], defn["bad"], defn["invert"])

        weighted_sum += score * defn["weight"]
        total_weight += defn["weight"]

        subscores.append(SubScore(
            name=defn["name"],
            value=round(float(value), 6),
            score=round(score, 1),
        ))

    final_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
    final_score = max(0.0, min(100.0, final_score))

    if final_score > 70:
        label = "Уверенно"
    elif final_score >= 40:
        label = "Средне"
    else:
        label = "Неуверенно"

    hnr_value = features.get("HNRdBACF_sma3nz_amean", 99.0)
    is_noisy = float(hnr_value) < NOISE_HNR_THRESHOLD

    return ConfidenceResult(
        score=final_score,
        label=label,
        subscores=subscores,
        hnr_value=round(float(hnr_value), 2),
        is_noisy=is_noisy,
    )
