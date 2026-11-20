"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Voice services

/api/transcribe  (POST audio file) -> faster-whisper local STT
/api/tts?text=..                 -> pyttsx3 offline TTS (Windows SAPI /
                                    Linux espeak) returned as WAV.

Both degrade gracefully: the endpoint replies with a clear error if the
optional dependency isn't installed instead of crashing the app.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import configs as config

log = logging.getLogger("voice")

# --------------------------------------------------------------------- #
#  Speech-to-text (faster-whisper, lazy model load, cached)
# --------------------------------------------------------------------- #
_whisper = None


def _get_whisper():
    global _whisper
    if _whisper is not None:
        return _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    _whisper = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper


async def transcribe(data: bytes, suffix: str = ".webm",
                     language: Optional[str] = None) -> str:
    model = _get_whisper()
    if model is None:
        return ("ERROR: faster-whisper not installed â€” "
                "pip install faster-whisper")

    tmp = config.MEMORY_DIR / f"upload_{int(time.time())}{suffix}"
    tmp.write_bytes(data)
    try:
        def _run():
            segs, _info = model.transcribe(
                str(tmp), language=language,
                beam_size=1,
            )
            return " ".join(s.text.strip() for s in segs).strip()

        text = await asyncio.to_thread(_run)
        return text or "[no speech detected]"
    except Exception as exc:
        return f"ERROR: transcription failed: {exc}"
    finally:
        tmp.unlink(missing_ok=True)


# --------------------------------------------------------------------- #
#  Text-to-speech (pyttsx3 offline, thread-safe single engine per call)
# --------------------------------------------------------------------- #
def _tts_dir() -> Path:
    d = config.BACKEND_DIR / "data" / "tts"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def synthesize(text: str) -> Path | None:
    """Render text to a WAV via pyttsx3; returns path or None."""
    try:
        import pyttsx3
    except ImportError:
        return None

    out = _tts_dir() / f"tts_{int(time.time())}_{abs(hash(text)) % 9999}.wav"

    def _run():
        engine = pyttsx3.init()
        engine.save_to_file(text[:1500], str(out))
        engine.runAndWait()

    try:
        await asyncio.to_thread(_run)
        return out if out.exists() else None
    except Exception as exc:
        log.warning("tts failed: %s", exc)
        return None
