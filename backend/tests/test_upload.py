import io
import wave
import struct
import math
import pytest
import numpy as np
import soundfile as sf
from httpx import AsyncClient, ASGITransport
from app.main import app


def _make_wav_bytes(duration_sec: float = 1.0, sr: int = 16000) -> bytes:
    """Генерирует валидный WAV в памяти."""
    n_samples = int(sr * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for _ in range(n_samples):
            wf.writeframes(struct.pack("<h", 0))
    return buf.getvalue()


def _make_ogg_bytes(duration_sec: float = 1.0, sr: int = 16000) -> bytes:
    n = int(sr * duration_sec)
    audio = np.zeros(n, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="OGG", subtype="VORBIS")
    return buf.getvalue()


@pytest.mark.anyio
async def test_upload_and_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        wav_bytes = _make_wav_bytes(2.0)
        files = [
            ("translations", ("tr1.wav", wav_bytes, "audio/wav")),
            ("translations", ("tr2.wav", wav_bytes, "audio/wav")),
        ]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] == "processing"

        session_id = data["session_id"]

        import asyncio
        await asyncio.sleep(2)

        resp2 = await client.get(f"/api/results/{session_id}")
        assert resp2.status_code == 200
        result = resp2.json()
        assert result["status"] == "done"
        assert "original" not in result
        assert len(result["translations"]) == 2
        tr = result["translations"][0]
        assert tr["duration_sec"] > 0
        assert tr["audio_url"].endswith(".wav")
        assert "lld" in tr
        assert "F0" in tr["lld"]
        assert "Loudness" in tr["lld"]
        assert "confidence_score" in tr
        assert "confidence_label" in tr
        assert tr["confidence_label"] in ("Уверенно", "Средне", "Неуверенно")
        assert 0 <= tr["confidence_score"] <= 100


@pytest.mark.anyio
async def test_upload_bad_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("orig.txt", b"not audio", "text/plain"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_results_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/results/nonexistent")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_upload_ogg():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ogg_bytes = _make_ogg_bytes(1.5)
        wav_bytes = _make_wav_bytes(1.5)
        files = [
            ("translations", ("tr1.ogg", ogg_bytes, "audio/ogg")),
            ("translations", ("tr2.wav", wav_bytes, "audio/wav")),
        ]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        import asyncio
        await asyncio.sleep(3)

        resp2 = await client.get(f"/api/results/{session_id}")
        result = resp2.json()
        assert result["status"] == "done"
        assert len(result["translations"]) == 2
        assert result["translations"][0]["duration_sec"] > 0
