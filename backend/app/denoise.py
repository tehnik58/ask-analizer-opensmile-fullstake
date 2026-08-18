from pathlib import Path
import numpy as np
import soundfile as sf
import noisereduce as nr


def denoise_file(path: Path) -> None:
    """Очищает WAV-файл от шума (spectral gating, non-stationary). Перезаписывает файл на месте."""
    audio, sr = sf.read(str(path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
        return
    cleaned = nr.reduce_noise(y=audio.astype(np.float32), sr=sr, stationary=False)
    sf.write(str(path), cleaned, sr, subtype="PCM_16")
