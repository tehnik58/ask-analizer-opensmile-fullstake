import io
import wave
import struct
import pytest
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


@pytest.mark.anyio
async def test_upload_and_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        wav_bytes = _make_wav_bytes(2.0)
        files = [
            ("original", ("orig.wav", wav_bytes, "audio/wav")),
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
        assert result["original"]["duration_sec"] > 0
        assert result["original"]["audio_url"].endswith(".wav")
        assert "lld" in result["original"]
        assert "F0" in result["original"]["lld"]
        assert "Loudness" in result["original"]["lld"]
        assert len(result["translations"]) == 2
        tr = result["translations"][0]
        assert "confidence_score" in tr
        assert "confidence_label" in tr
        assert tr["confidence_label"] in ("Уверенно", "Средне", "Неуверенно")
        assert 0 <= tr["confidence_score"] <= 100
        assert "lld" in tr


@pytest.mark.anyio
async def test_upload_bad_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("original", ("orig.txt", b"not audio", "text/plain"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_results_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/results/nonexistent")
        assert resp.status_code == 404
