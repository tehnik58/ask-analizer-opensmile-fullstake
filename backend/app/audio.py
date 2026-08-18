import io
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .download import download_audio

NATIVE_EXTENSIONS = {".wav", ".mp3", ".ogg", ".opus", ".flac", ".aiff", ".aif", ".au", ".caf", ".w64"}
FFMPEG_EXTENSIONS = {".m4a", ".mp4", ".aac", ".wma", ".amr", ".webm", ".3gp", ".oga", ".mp2"}
ALLOWED_EXTENSIONS = NATIVE_EXTENSIONS | FFMPEG_EXTENSIONS
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
TARGET_SR = 16000


def _get_ffmpeg_exe() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def validate_file(filename: str, file_size: int) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Неподдерживаемый формат: {ext}. Допустимы: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if file_size > MAX_FILE_SIZE:
        return f"Файл слишком большой: {file_size / 1024 / 1024:.1f} МБ (макс 20 МБ)"
    return None


def _convert_with_ffmpeg(input_path: Path, output_path: Path) -> None:
    ffmpeg = _get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-i", str(input_path),
        "-ar", str(TARGET_SR), "-ac", "1", "-f", "wav", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode(errors='replace')[:200]}")


def _read_duration(path: Path) -> float:
    info = sf.info(str(path))
    return info.duration


def convert_to_wav(input_bytes: bytes, original_name: str, output_path: Path) -> float:
    """Конвертирует аудио в WAV 16kHz моно. Возвращает длительность в секундах."""
    ext = Path(original_name).suffix.lower()
    is_ffmpeg = ext in FFMPEG_EXTENSIONS

    if not is_ffmpeg:
        # Нативный путь — soundfile + librosa
        try:
            audio, sr = sf.read(io.BytesIO(input_bytes))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != TARGET_SR:
                import librosa
                audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=TARGET_SR)
                sr = TARGET_SR
            sf.write(str(output_path), audio, sr, subtype="PCM_16")
            return len(audio) / sr
        except Exception:
            # Fallback на ffmpeg если нативное чтение не удалось
            is_ffmpeg = True

    if is_ffmpeg:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
            tmp_in.write(input_bytes)
            tmp_in_path = Path(tmp_in.name)
        try:
            _convert_with_ffmpeg(tmp_in_path, output_path)
            return _read_duration(output_path)
        finally:
            tmp_in_path.unlink(missing_ok=True)


def convert_url_to_wav(url: str) -> tuple[Path, float]:
    """Download audio from URL, convert to WAV 16kHz mono in a temp file.

    Returns:
        (temp_path, duration): path to temp WAV file and duration in seconds.
        Caller is responsible for deleting temp_path.
    """
    data, filename = download_audio(url)
    tmp = Path(tempfile.mktemp(suffix=".wav"))
    duration = convert_to_wav(data, filename, tmp)
    return tmp, duration
