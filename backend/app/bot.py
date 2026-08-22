"""Telegram bot over the speech-confidence analyzer library.

Run from backend/:
    BOT_TOKEN=123:abc python -m app.bot
"""

import asyncio
import html
import io
import logging
import os
import re
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message

from .analysis import AudioResult, analyze_bytes, analyze_translations
from .audio import ALLOWED_EXTENSIONS, validate_file
from .charts import render_lld_chart

logger = logging.getLogger(__name__)
router = Router()

MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # Bot API refuses files above 20 MB

HELP_TEXT = (
    "<b>Анализатор уверенности речи</b>\n\n"
    "Пришлите аудиофайл (wav/mp3/ogg/m4a…), голосовое сообщение или ссылку "
    "http(s) на запись — я оценю уверенность речи: балл 0–100, разбор по "
    "метрикам и графики F0/Loudness/Jitter.\n\n"
    "Каждый файл анализируется отдельно."
)

_MIME_EXT = {
    "audio/ogg": ".ogg",
    "audio/vorbis": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
}

_URL_RE = re.compile(r"(?i)^https?://\S+$")


def _format_result(result: AudioResult) -> str:
    c = result.confidence
    lines = [
        "<b>Результат анализа</b>",
        f"Длительность: {result.duration_sec:g} с",
        f"Уверенность: <b>{c.score:g}/100</b> — <i>{c.label}</i>",
    ]
    if c.is_noisy:
        lines.append("\u26a0\ufe0f Запись шумная, оценка может быть неточной")
    lines.append("")
    lines.append("<b>Субскоры</b>")
    for s in c.subscores:
        filled = max(0, min(10, round(s.score / 10)))
        bar = "\u25ac" * filled + "\u2501" * (10 - filled)
        lines.append(f"{html.escape(s.name)}  {bar}  {s.score:g}")
    return "\n".join(lines)[:1024]


def _extract_source(message: Message) -> tuple[str, str, int] | None:
    """Return (file_id, filename, size) for an audio-bearing message."""
    if message.voice:
        return message.voice.file_id, f"voice_{message.message_id}.ogg", message.voice.file_size or 0
    if message.audio:
        name = message.audio.file_name or f"audio{_MIME_EXT.get(message.audio.mime_type or '', '.mp3')}"
        return message.audio.file_id, name, message.audio.file_size or 0
    if message.document:
        doc = message.document
        mime = doc.mime_type or ""
        ext = Path(doc.file_name or "").suffix.lower()
        if not (mime.startswith("audio/") or ext in ALLOWED_EXTENSIONS):
            return None
        return doc.file_id, doc.file_name or f"file{ext}", doc.file_size or 0
    return None


async def _download_bytes(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, destination=buf)
    return buf.getvalue()


async def _send_result(message: Message, result: AudioResult) -> None:
    text = _format_result(result)
    try:
        png = render_lld_chart(result.lld, result.duration_sec)
        await message.answer_photo(BufferedInputFile(png, filename="lld.png"), caption=text)
    except Exception:
        logger.exception("Chart rendering/sending failed")
        await message.answer(text)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(F.voice | F.audio | F.document)
async def handle_audio(message: Message, bot: Bot) -> None:
    source = _extract_source(message)
    if source is None:
        await message.answer("Это не похоже на аудиофайл. Пришлите голосовое, аудио или документ с аудио.")
        return
    file_id, filename, size = source

    err = validate_file(filename, size)
    if err:
        await message.answer(html.escape(err))
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        data = await _download_bytes(bot, file_id)
        result = await asyncio.to_thread(
            analyze_bytes, data, filename, f"user{message.from_user.id}_{message.message_id}"
        )
    except ValueError as e:
        await message.answer(f"\u26a0\ufe0f {html.escape(str(e))}")
        return
    except Exception:
        logger.exception("Analysis failed for %s", filename)
        await message.answer("\u26a0\ufe0f Не удалось проанализировать запись. Попробуйте другой файл.")
        return
    await _send_result(message, result)


@router.message(F.text.regexp(_URL_RE))
async def handle_url(message: Message, bot: Bot) -> None:
    url = (message.text or "").strip()
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        results = await asyncio.to_thread(
            analyze_translations, [{"id": f"url_{message.message_id}", "url": url}]
        )
    except ValueError as e:
        await message.answer(f"\u26a0\ufe0f {html.escape(str(e))}")
        return
    except RuntimeError:
        await message.answer("\u26a0\ufe0f Не удалось скачать аудио по ссылке.")
        return
    except Exception:
        logger.exception("URL analysis failed for %s", url)
        await message.answer("\u26a0\ufe0f Ошибка анализа. Проверьте ссылку и попробуйте снова.")
        return
    for r in results:
        await _send_result(message, r)


@router.message(F.text)
async def handle_other_text(message: Message) -> None:
    await message.answer("Пришлите аудиофайл, голосовое сообщение или ссылку http(s) на аудио.\n\n/start — справка")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Понимаю только аудио, голосовые сообщения и ссылки на аудиофайлы.")


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        sys.exit("BOT_TOKEN environment variable is required")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
