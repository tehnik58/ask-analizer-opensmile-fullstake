"""OpenSMILE анализ: заглушка для Phase 1, будет реализовано в Phase 2."""
from pathlib import Path


def analyze_session(session_id: str, session_dir: Path):
    """Заглушка — просто помечает сессию как done."""
    from .sessions import get_session, set_results
    session = get_session(session_id)

    results = {
        "original": {
            "audio_url": f"/static/{session_id}/original.wav",
            "duration_sec": session["original"]["duration"],
            "lld": {"F0": [], "Loudness": [], "Jitter": []},
        },
        "translations": [],
    }

    for tr in session["translations"]:
        results["translations"].append({
            "id": tr["id"],
            "audio_url": f"/static/{session_id}/{tr['path'].name}",
            "duration_sec": tr["duration"],
            "confidence_score": 50,
            "confidence_label": "Средне",
            "lld": {"F0": [], "Loudness": [], "Jitter": []},
        })

    set_results(session_id, results)
