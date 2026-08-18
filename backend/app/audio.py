import io
import numpy as np
import soundfile as sf
from pathlib import Path

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
TARGET_SR = 16000


def validate_file(filename: str, file_size: int) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Неподдерживаемый формат: {ext}. Допустимы: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > MAX_FILE_SIZE:
        return f"Файл слишком большой: {file_size / 1024 / 1024:.1f} МБ (макс 20 МБ)"
    return None


def convert_to_wav(input_bytes: bytes, original_name: str, output_path: Path) -> float:
    """Конвертирует аудио в WAV 16kHz моно. Возвращает длительность в секундах."""
    ext = Path(original_name).suffix.lower()

    if ext == ".mp3":
        import librosa
        audio, sr = librosa.load(io.BytesIO(input_bytes), sr=TARGET_SR, mono=True)
    else:
        audio, sr = sf.read(io.BytesIO(input_bytes))
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != TARGET_SR:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

    sf.write(str(output_path), audio, sr, subtype="PCM_16")
    duration = len(audio) / sr
    return duration
