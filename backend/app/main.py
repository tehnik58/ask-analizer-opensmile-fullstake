import asyncio
import shutil
import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .sessions import create_session, get_session, set_status, get_results_for_api, DATA_DIR
from .audio import validate_file, convert_to_wav
from .denoise import denoise_file

app = FastAPI(title="Translation Confidence Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")


def _get_frontend_dist() -> Path | None:
    """Возвращает путь к собранному фронтенду или None (для dev-режима)."""
    if getattr(sys, "frozen", False):
        # PyInstaller — dist лежит рядом с exe в подпапке web/
        base = Path(sys._MEIPASS)
        dist = base / "web"
    else:
        # Dev: backend/../frontend/dist
        dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    return dist if dist.is_dir() else None


def _run_analysis(session_id: str, session_dir: Path):
    """Фоновая задача анализа (заглушка — заполнится в Фазе 2)."""
    try:
        from .analysis import analyze_session
        analyze_session(session_id, session_dir)
    except Exception as e:
        set_status(session_id, "error", error=str(e))


@app.post("/api/upload/")
async def upload(
    translations: list[UploadFile] = File(...),
):
    if not translations:
        raise HTTPException(400, "Загрузите хотя бы одну запись")

    session_id = create_session()
    session_dir = DATA_DIR / session_id

    # Сохраняем записи
    for i, tr in enumerate(translations):
        tr_bytes = await tr.read()
        err = validate_file(tr.filename, len(tr_bytes))
        if err:
            raise HTTPException(422, f"{tr.filename}: {err}")
        raw_path = session_dir / f"translation_{i}_raw.wav"
        tr_dur = convert_to_wav(tr_bytes, tr.filename, raw_path)
        # Denoised копия — только для плеера; анализ идёт по raw
        denoised_path = session_dir / f"translation_{i}.wav"
        shutil.copy2(raw_path, denoised_path)
        denoise_file(denoised_path)
        session = get_session(session_id)
        session["translations"].append({
            "id": f"trans_{i}",
            "filename": tr.filename,
            "path": denoised_path,
            "raw_path": raw_path,
            "duration": tr_dur,
        })

    # Запускаем анализ в фоне
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_analysis, session_id, session_dir)

    return {"session_id": session_id, "status": "processing"}


@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    result = get_results_for_api(session_id)
    if result is None:
        raise HTTPException(404, "Сессия не найдена")
    return result


# --- Раздача фронтенда (dev и desktop) ---

_frontend_dist = _get_frontend_dist()

if _frontend_dist:
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(_frontend_dist / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = _frontend_dist / path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_frontend_dist / "index.html"))
