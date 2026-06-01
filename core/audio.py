"""Microphone capture (push-to-talk) and PCM playback with RMS level callbacks."""
from __future__ import annotations
import queue
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

MIC_RATE = 16000          # faster-whisper expects 16 kHz mono
TTS_RATE = 24000          # ElevenLabs pcm_24000

LevelCb = Optional[Callable[[float], None]]   # 0..1 RMS, for the HUD waveform


def _rms(frames: np.ndarray) -> float:
    if frames.size == 0:
        return 0.0
    return float(min(1.0, np.sqrt(np.mean(frames.astype(np.float32) ** 2)) * 4.0))


class Recorder:
    """Records mic audio between start() and stop(); reports input level."""

    def __init__(self, on_level: LevelCb = None):
        self.on_level = on_level
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None

    def _cb(self, indata, frames, time_, status):  # noqa: ANN001
        mono = indata[:, 0].copy()
        self._q.put(mono)
        if self.on_level:
            self.on_level(_rms(mono))

    def start(self) -> None:
        while not self._q.empty():
            self._q.get_nowait()
        self._stream = sd.InputStream(
            samplerate=MIC_RATE, channels=1, dtype="float32", callback=self._cb
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        chunks = []
        while not self._q.empty():
            chunks.append(self._q.get_nowait())
        if self.on_level:
            self.on_level(0.0)
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


def play_pcm_stream(pcm_chunks, on_level: LevelCb = None) -> None:
    """Play an iterable of raw int16 PCM byte chunks (mono, TTS_RATE)."""
    with sd.OutputStream(samplerate=TTS_RATE, channels=1, dtype="int16") as out:
        for chunk in pcm_chunks:
            if not chunk:
                continue
            samples = np.frombuffer(chunk, dtype=np.int16)
            out.write(samples)
            if on_level:
                on_level(_rms(samples.astype(np.float32) / 32768.0))
    if on_level:
        on_level(0.0)
