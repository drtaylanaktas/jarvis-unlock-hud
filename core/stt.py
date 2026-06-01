"""Speech-to-text via local faster-whisper (offline, no API key)."""
from __future__ import annotations
import asyncio

import numpy as np
from faster_whisper import WhisperModel

from audio import MIC_RATE


class STT:
    def __init__(self, cfg: dict):
        s = cfg["stt"]
        size = s.get("model", "base")
        self.language = s.get("language", "en")
        # int8 on CPU is fast and light on Apple Silicon.
        self._model = WhisperModel(size, device="cpu", compute_type="int8")

    def _sync_transcribe(self, audio: np.ndarray) -> str:
        if audio.size < MIC_RATE // 4:   # < 0.25s — treat as empty
            return ""
        lang = None if self.language in ("auto", "") else self.language
        segments, _ = self._model.transcribe(audio, language=lang, beam_size=1)
        return " ".join(seg.text for seg in segments).strip()

    async def transcribe(self, audio: np.ndarray) -> str:
        return await asyncio.to_thread(self._sync_transcribe, audio)
