# AGENTS.md

Speech-confidence analyzer ("Translation Confidence Analyzer"). Upload audio → OpenSMILE extracts acoustic features (F0, Loudness, Jitter) → confidence score 0–100 with labels. Two components: `backend/` (FastAPI), `frontend/` (React + Vite + Recharts + Howler).

## Components & entrypoints
- Backend: `backend/app/main.py` (FastAPI app). Run from `backend/`:
  - `uvicorn app.main:app --reload --port 8000`
  - Tests: `pytest` (run from `backend/` — imports use top-level `app.*`)
- Frontend: `frontend/`. `npm run dev` (Vite proxies `/api` and `/static` → `localhost:8000`), `npm run build`, `npm run lint` = **oxlint**, not ESLint.

## Audio pipeline (non-obvious)
- Upload `/api/upload/` currently accepts **only `translations`** files — the PRD's `original` field is not implemented. Trust `app/main.py`, not `prd.md`.
- Two copies per file: `translation_N.wav` (denoised) and `translation_N_raw.wav`. **LLD charts + playback use denoised; confidence scoring uses RAW** (denoise distorts F0Std/F1bandwidth). Keep this split if changing the pipeline.
- 19 formats supported via `soundfile` + bundled ffmpeg (`imageio_ffmpeg`); output normalized to 16 kHz mono WAV.
- LLD series use `None` (not 0) for silence/NaN frames — frontend renders these as gaps.

## Scoring
- 8 weighted subscores defined in `backend/app/scoring.py` (`METRIC_DEFS`): F0Std (U-shaped window), Jitter, HNR, VoicedFraction, Tempo, F1bandwidth, F0Range, RhythmCV. Weights sum to 1.0 there.
- Labels: `>70` Уверенно, `40–70` Средне, `<40` Неуверенно. `is_noisy` when HNR < 10.0.

## Testing quirks
- Uses `pytest` + `pytest-anyio` (see `conftest.py`).
- Integration tests (`test_upload*.py`, parts of `test_analysis.py`) run **real OpenSMILE** and the background analysis task, with `asyncio.sleep(2–3s)` waits — slow and dependent on OpenSMILE being installed. `test_analysis.py` has hardcoded regression profiles (raw feature dicts) that pin expected score ranges — be careful adjusting scoring thresholds/weights.
- Backend data/sessions are in-memory (`backend/app/sessions.py`), persisted to `backend/data/` (gitignored).

## Doc drift
- `prd.md` describes intended full product and is ahead of / inconsistent with the code (e.g. `original` upload, Chart.js/Howler choices). Treat it as product intent; the code is the source of truth.