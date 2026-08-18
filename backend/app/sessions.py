import uuid
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

_sessions: dict[str, dict] = {}
_lock = Lock()


def create_session() -> str:
    session_id = uuid.uuid4().hex[:12]
    session_dir = DATA_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    with _lock:
        _sessions[session_id] = {
            "session_id": session_id,
            "status": "processing",
            "dir": session_dir,
            "original": None,
            "translations": [],
            "results": None,
            "error": None,
        }
    return session_id


def get_session(session_id: str) -> dict | None:
    with _lock:
        return _sessions.get(session_id)


def set_status(session_id: str, status: str, error: str | None = None):
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["status"] = status
            _sessions[session_id]["error"] = error


def set_results(session_id: str, results: dict):
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["results"] = results
            _sessions[session_id]["status"] = "done"


def get_results_for_api(session_id: str) -> dict | None:
    s = get_session(session_id)
    if s is None:
        return None
    return {
        "session_id": s["session_id"],
        "status": s["status"],
        "error": s.get("error"),
        "original": s["results"]["original"] if s["results"] else None,
        "translations": s["results"]["translations"] if s["results"] else [],
    }
