"""Text-to-speech via ElevenLabs (British voice), streamed to the speakers."""
from __future__ import annotations
import asyncio
import os

from elevenlabs.client import ElevenLabs

import audio


class TTS:
    def __init__(self, cfg: dict, on_level=None):
        t = cfg["tts"]
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", t.get("voice_id"))
        self.model_id = t.get("model_id", "eleven_turbo_v2_5")
        self.on_level = on_level
        self.client = ElevenLabs()  # reads ELEVENLABS_API_KEY

    def _sync_speak(self, text: str) -> None:
        # Stream raw PCM at 24 kHz so we can play + measure level without ffmpeg.
        stream = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            text=text,
            output_format="pcm_24000",
        )
        audio.play_pcm_stream(stream, self.on_level)

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        await asyncio.to_thread(self._sync_speak, text)
