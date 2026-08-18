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
from app import analyze_translations

results = analyze_translations([
    {"id": "student_1", "url": "https://example.com/recording.mp3"},
])

r = results[0]
print(f"Score: {r.confidence.score}")   # 78.3
print(f"Label: {r.confidence.label}")   # "Уверенно"
print(f"LLD F0: {r.lld['F0'][:5]}")    # [45.2, 46.1, ...]
```

## API

### `analyze_translations(translations) -> list[AudioResult]`

Основная функция. Скачивает аудио по URL, конвертирует, шумоподавляет, анализирует.

**Аргументы:**
- `translations` — список dict:
  - `id` (str) — идентификатор записи
  - `url` (str) — URL аудио (`http://`, `https://`, `file:///`)

**Возвращает:** `list[AudioResult]`

### `AudioResult`

| Поле | Тип | Описание |
|---|---|---|
| `id` | str | Идентификатор |
| `audio_url` | str | Исходный URL |
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
| `download_audio(url)` | Скачивание по URL (bytes, filename) |
| `convert_url_to_wav(url)` | URL → WAV 16kHz mono (temp file) |
| `convert_to_wav(bytes, name, path)` | Конвертация байтов в WAV |
| `validate_file(filename, size)` | Проверка формата и размера |
| `denoise_file(path)` | Шумоподавление (in-place) |
| `extract_lld(audio_path)` | Извлечение LLD-признаков |
| `compute_confidence(...)` | Прямой вызов скоринга |

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
