"""Тесты поддержки различных аудиоформатов."""
import io
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from httpx import AsyncClient, ASGITransport
from app.main import app

SR = 16000
DURATION = 1.0
N = int(SR * DURATION)


def _sine() -> np.ndarray:
    t = np.linspace(0, DURATION, N, dtype=np.float32)
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    sf.write(buf, _sine(), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _native_bytes(fmt: str, subtype: str | None = None) -> bytes:
    buf = io.BytesIO()
    kwargs = {"format": fmt}
    if subtype:
        kwargs["subtype"] = subtype
    sf.write(buf, _sine(), SR, **kwargs)
    return buf.getvalue()


def _ffmpeg_bytes(in_fmt: str, ext: str) -> bytes:
    """Генерирует аудио через ffmpeg (кодирование в нужный формат)."""
    from imageio_ffmpeg import get_ffmpeg_exe
    wav_path = Path(tempfile.mktemp(suffix=".wav"))
    out_path = Path(tempfile.mktemp(suffix=ext))
    sf.write(str(wav_path), _sine(), SR, subtype="PCM_16")
    try:
        cmd = [get_ffmpeg_exe(), "-y", "-i", str(wav_path), str(out_path)]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        return out_path.read_bytes()
    finally:
        wav_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)


# --- Нативные форматы (soundfile) ---

@pytest.mark.anyio
async def test_upload_flac():
    flac = _native_bytes("FLAC")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("test.flac", flac, "audio/flac"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        import asyncio
        await asyncio.sleep(2)
        r = (await client.get(f"/api/results/{sid}")).json()
        assert r["status"] == "done"
        assert r["translations"][0]["duration_sec"] > 0


@pytest.mark.anyio
async def test_upload_aiff():
    aiff = _native_bytes("AIFF")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("test.aiff", aiff, "audio/aiff"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200


# --- Форматы через ffmpeg ---

@pytest.mark.anyio
async def test_upload_m4a():
    m4a = _ffmpeg_bytes("aac", ".m4a")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("test.m4a", m4a, "audio/mp4"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        import asyncio
        await asyncio.sleep(3)
        r = (await client.get(f"/api/results/{sid}")).json()
        assert r["status"] == "done"
        assert r["translations"][0]["duration_sec"] > 0


@pytest.mark.anyio
async def test_upload_webm():
    webm = _ffmpeg_bytes("libopus", ".webm")
    if not webm:
        pytest.skip("ffmpeg не поддерживает libopus")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("test.webm", webm, "audio/webm"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 200


# --- Негативные ---

@pytest.mark.anyio
async def test_upload_reject_exe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("virus.exe", b"MZ\x90\x00", "application/octet-stream"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_upload_reject_txt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("translations", ("note.txt", b"hello", "text/plain"))]
        resp = await client.post("/api/upload/", files=files)
        assert resp.status_code == 422
