from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlparse


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
DOWNLOAD_TIMEOUT = 30  # seconds


def download_audio(url: str) -> tuple[bytes, str]:
    """
    Download audio from URL.

    Supports http://, https://, and file:/// (local files).

    Returns:
        (bytes, filename): audio content and original filename.

    Raises:
        ValueError: on invalid URL or file too large.
        RuntimeError: on download failure.
    """
    parsed = urlparse(url)

    if parsed.scheme == "file":
        return _read_local(parsed.path)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")

    filename = Path(parsed.path).name or "audio.wav"

    try:
        req = Request(url, headers={"User-Agent": "TCA/1.0"})
        with urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            data = resp.read(MAX_FILE_SIZE + 1)
            if len(data) > MAX_FILE_SIZE:
                raise ValueError(f"File too large: {len(data) / 1024 / 1024:.1f} MB (max 50 MB)")
            return data, filename
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e


def _read_local(path: str) -> tuple[bytes, str]:
    """Read a local file via file:/// URL."""
    # On Windows, urlparse gives /C:/path — strip leading /
    if len(path) > 2 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    p = Path(path)
    if not p.exists():
        raise ValueError(f"File not found: {path}")
    if p.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {p.stat().st_size / 1024 / 1024:.1f} MB (max 50 MB)")
    return p.read_bytes(), p.name
