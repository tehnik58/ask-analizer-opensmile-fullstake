import shutil
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import noisereduce as nr

from .audio import convert_url_to_wav


def denoise_file(path: Path) -> None:
    """Denoise a WAV file in place (spectral gating, non-stationary)."""
    audio, sr = sf.read(str(path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
        return
    cleaned = nr.reduce_noise(y=audio.astype(np.float32), sr=sr, stationary=False)
    sf.write(str(path), cleaned, sr, subtype="PCM_16")


def denoise_url(url: str) -> tuple[Path, float]:
    """Download, convert to WAV, and denoise.

    Returns:
        (temp_path, duration): path to denoised temp WAV and duration in seconds.
        Caller is responsible for deleting temp_path.
    """
    raw_path, duration = convert_url_to_wav(url)
    denoise_file(raw_path)
    return raw_path, duration
