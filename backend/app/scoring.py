"""
Модуль скоринга уверенности речи.

6 суб-скоров 0–100 с насыщением (линейная интерполяция good→bad, clamp).
Итоговый скор = взвешенная сумма.
"""

from dataclasses import dataclass


@dataclass
class SubScore:
    name: str
    value: float
    score: float
    good: float
    bad: float


@dataclass
class ConfidenceResult:
    score: float
    label: str
    subscores: list[SubScore]
    hnr_value: float
    is_noisy: bool


# Пороговые значения: (good, bad) — good = «уверенно», bad = «неуверенно»
# Если bad > good (например jitter), то score = map(value, bad, good) → инверсия
# Если good > bad (например HNR), то score = map(value, bad, good)

METRIC_DEFS = {
    "F0Std": {
        "name": "F0 вариативность",
        "feature": "F0semitoneFrom27.5Hz_sma3nz_stddevNorm",
        "good": 0.10,   # низкий разброс → монотонно, уверенно
        "bad": 0.35,    # высокий разброс → дрожание
        "invert": True, # lower value = higher score
        "weight": 0.25,
    },
    "F0Mean": {
        "name": "F0 средний тон",
        "feature": "F0semitoneFrom27.5Hz_sma3nz_amean",
        "good": 35.0,   # более высокий тон → увереннее
        "bad": 20.0,
        "invert": False,
        "weight": 0.10,
    },
    "Jitter": {
        "name": "Jitter (дрожание)",
        "feature": "jitterLocal_sma3nz_amean",
        "good": 0.005,  # 0.5% — чистый голос
        "bad": 0.040,   # 4% — патология
        "invert": True,
        "weight": 0.20,
    },
    "HNR": {
        "name": "HNR (гармоничность)",
        "feature": "HNRdBACF_sma3nz_amean",
        "good": 15.0,   # чистый голос
        "bad": 3.0,     # очень шумный
        "invert": False,
        "weight": 0.20,
    },
    "VoicedFraction": {
        "name": "Доля речи",
        "feature": None,  # вычисляется из LLD отдельно
        "good": 0.80,
        "bad": 0.40,
        "invert": False,
        "weight": 0.15,
    },
    "Tempo": {
        "name": "Темп речи",
        "feature": "loudnessPeaksPerSec",
        "good": 4.0,    # быстрая речь → увереннее
        "bad": 1.5,     # медленная → неувереннее
        "invert": False,
        "weight": 0.10,
    },
}

NOISE_HNR_THRESHOLD = 10.0  # дБ — ниже этого значения запись считается шумной


def _subscore(value: float, good: float, bad: float, invert: bool) -> float:
    """Линейная интерполяция 0–100 с clamp."""
    if invert:
        # lower value = better score
        if value <= good:
            return 100.0
        if value >= bad:
            return 0.0
        return max(0.0, min(100.0, (bad - value) / (bad - good) * 100))
    else:
        # higher value = better score
        if value >= good:
            return 100.0
        if value <= bad:
            return 0.0
        return max(0.0, min(100.0, (value - bad) / (good - bad) * 100))


def compute_confidence(features: dict, voiced_fraction: float) -> ConfidenceResult:
    """
    Вычисляет скор уверенности.

    features: dict с ключами из METRIC_DEFS[*]["feature"]
    voiced_fraction: доля кадров с голосом (0–1)
    """
    subscores = []
    weighted_sum = 0.0
    total_weight = 0.0

    for key, defn in METRIC_DEFS.items():
        if defn["feature"] is not None:
            value = features.get(defn["feature"], 0.0)
        else:
            value = voiced_fraction

        score = _subscore(value, defn["good"], defn["bad"], defn["invert"])
        weighted_sum += score * defn["weight"]
        total_weight += defn["weight"]

        subscores.append(SubScore(
            name=defn["name"],
            value=round(float(value), 6),
            score=round(score, 1),
            good=defn["good"],
            bad=defn["bad"],
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
