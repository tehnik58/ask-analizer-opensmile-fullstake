# Translation Confidence Analyzer — Micro Module

Анализатор уверенности речи по аудиозаписям. Библиотека для подключения к любому Python-бэкенду.

## Установка

```bash
pip install git+https://github.com/user/language-analizer.git@micro
```

или локально:

```bash
git clone -b micro https://github.com/user/language-analizer.git
cd language-analizer/backend
pip install -r requirements.txt
```

## Быстрый старт

```python
from pathlib import Path
from app import analyze_translations, convert_to_wav, denoise_file

# Конвертация в WAV (если нужно)
wav_path = convert_to_wav(audio_bytes, "recording.mp3", Path("output.wav"))

# Шумоподавление (опционально)
denoise_file(wav_path)

# Анализ
results = analyze_translations([{
    "id": "student_1",
    "path": wav_path,
    "duration": 12.5,  # секунды
}])

r = results[0]
print(f"Score: {r.confidence.score}")       # 78.3
print(f"Label: {r.confidence.label}")       # "Уверенно"
print(f"LLD F0: {r.lld['F0'][:5]}")        # [45.2, 46.1, ...]
```

## API

### `analyze_translations(translations) -> list[AudioResult]`

Основная функция. Принимает список аудио, возвращает результаты анализа.

**Аргументы:**
- `translations` — список dict:
  - `id` (str) — идентификатор записи
  - `path` (Path) — путь к аудиофайлу (WAV рекомендуется)
  - `raw_path` (Path, необязательно) — путь к исходному аудио для скоринга (по умолчанию = path)
  - `duration` (float) — длительность в секундах

**Возвращает:** `list[AudioResult]`

### `AudioResult`

| Поле | Тип | Описание |
|---|---|---|
| `id` | str | Идентификатор |
| `audio_path` | Path | Путь к аудио |
| `duration_sec` | float | Длительность (сек) |
| `confidence` | ConfidenceResult | Результат скоринга |
| `lld` | dict | Низкоуровневые признаки (F0, Loudness, Jitter) |

### `ConfidenceResult`

| Поле | Тип | Описание |
|---|---|---|
| `score` | float | Балл 0–100 |
| `label` | str | "Уверенно" / "Средне" / "Неуверенно" |
| `subscores` | list[SubScore] | 8 субскоров |
| `hnr_value` | float | HNR значение |
| `is_noisy` | bool | Шумная запись |

### Вспомогательные функции

| Функция | Описание |
|---|---|
| `convert_to_wav(input_bytes, filename, output_path)` | Конвертирует аудио в WAV 16kHz mono |
| `validate_file(filename, file_size)` | Проверяет формат и размер |
| `denoise_file(path)` | Шумоподавление (модифицирует файл) |
| `extract_lld(audio_path)` | Извлечение LLD-признаков |

## Поддерживаемые форматы

10 нативных (soundfile): WAV, FLAC, OGG, AIFF, AIF, CAF, MP3, WMA, VOC, SOU
9 через ffmpeg: M4A, WebM, OPUS, AAC, WavPack, AMR, ALAC, AU, RAW

## Зависимости

```
opensmile>=2.6.0
numpy>=1.26.0
soundfile>=0.12.1
noisereduce>=3.0.0
imageio-ffmpeg>=0.6.0
librosa>=1.0.0
```
