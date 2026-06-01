"""J.A.R.V.I.S. core — WebSocket hub + push-to-talk pipeline.

Flow per turn:
  HUD sends {"type":"ptt","state":"down"}  -> start mic, broadcast state=listening
  HUD sends {"type":"ptt","state":"up"}    -> stop mic -> STT -> Claude (tools) -> ElevenLabs TTS
  broadcasts: state(listening|thinking|speaking|idle), level, transcript, tool, response, end
"""
from __future__ import annotations
import asyncio
import json

import websockets
from dotenv import load_dotenv

from google_client import load_config
import audio                       # for audio.INTERRUPT (mute)
from audio import Recorder
from stt import STT
from tts import TTS
from brain import Brain
from tools import DISPATCH

load_dotenv(override=True)  # core/.env -> ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, ... (wins over empty injected env)

# Spoken commands that instantly stop Jarvis (no brain call).
STOPWORDS = {"mute", "sus", "dur", "kes", "stop", "sessiz", "sessizleş", "sus bakalım", "kes sesini"}


class Hub:
    def __init__(self):
        self.cfg = load_config()
        self.clients: set = set()
        self.loop = asyncio.get_event_loop()
        self.busy = False
        self.task = None  # current turn (cancellable)
        # Level callbacks fire from audio threads -> bounce onto the loop.
        self.recorder = Recorder(on_level=lambda v: self._emit_level(v))
        self.stt = STT(self.cfg)
        self.tts = TTS(self.cfg, on_level=lambda v: self._emit_level(v))
        self.brain = Brain(self.cfg, DISPATCH)

    # ---- broadcasting -------------------------------------------------
    async def broadcast(self, msg: dict) -> None:
        if not self.clients:
            return
        data = json.dumps(msg)
        await asyncio.gather(*(c.send(data) for c in list(self.clients)),
                             return_exceptions=True)

    def _emit_level(self, v: float) -> None:
        # called from a sounddevice thread
        asyncio.run_coroutine_threadsafe(
            self.broadcast({"type": "level", "rms": v}), self.loop
        )

    # ---- session pipeline --------------------------------------------
    async def _on_ptt_down(self) -> None:
        if self.busy:
            return
        await self.broadcast({"type": "state", "value": "listening"})
        self.recorder.start()

    async def _on_ptt_up(self) -> None:
        if self.busy:
            return
        self.busy = True
        audio.INTERRUPT.clear()   # fresh turn — allow audio again
        try:
            recorded = self.recorder.stop()
            await self.broadcast({"type": "state", "value": "thinking"})
            text = await self.stt.transcribe(recorded)
            if not text:
                return
            await self.broadcast({"type": "transcript", "text": text})

            # Spoken stop command -> just go quiet, no brain call.
            if text.strip().lower().strip(".!?, ") in STOPWORDS:
                return

            self.task = asyncio.create_task(self._run_turn(text))
            try:
                await self.task
            except asyncio.CancelledError:
                pass  # muted mid-turn
        except Exception as e:  # keep the hub alive
            await self.broadcast({"type": "error", "message": str(e)})
        finally:
            self.task = None
            await self.broadcast({"type": "end"})
            await self.broadcast({"type": "state", "value": "idle"})
            self.busy = False

    async def _run_turn(self, text: str) -> None:
        started = {"v": False}

        async def on_sentence(sentence: str) -> None:
            if not started["v"]:
                started["v"] = True
                await self.broadcast({"type": "state", "value": "speaking"})
            await self.broadcast({"type": "response", "text": sentence, "final": False})
            await self.tts.speak(sentence)

        async def on_tool(name: str) -> None:
            await self.broadcast({"type": "tool", "name": name})

        await self.brain.respond(text, on_sentence, on_tool)
        await self.broadcast({"type": "response", "text": "", "final": True})

    async def _cancel(self) -> None:
        """Instant mute: stop playback now and abort the current turn."""
        audio.INTERRUPT.set()                 # break the playback loop immediately
        if self.task and not self.task.done():
            self.task.cancel()                # _on_ptt_up's finally cleans up
        else:
            await self.broadcast({"type": "end"})
            await self.broadcast({"type": "state", "value": "idle"})
            self.busy = False

    # ---- websocket handler -------------------------------------------
    async def handler(self, ws) -> None:
        self.clients.add(ws)
        try:
            await ws.send(json.dumps({"type": "state", "value": "idle"}))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "ptt":
                    if msg.get("state") == "down":
                        await self._on_ptt_down()
                    elif msg.get("state") == "up":
                        await self._on_ptt_up()
                elif msg.get("type") == "cancel":
                    await self._cancel()
        finally:
            self.clients.discard(ws)


async def main() -> None:
    hub = Hub()
    s = hub.cfg["server"]
    async with websockets.serve(hub.handler, s["host"], int(s["port"])):
        print(f"J.A.R.V.I.S. core listening on ws://{s['host']}:{s['port']}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
