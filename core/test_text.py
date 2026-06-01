"""Quick end-to-end brain test (no mic): text in -> Claude (+tools) -> spoken reply.
Usage:  core/.venv/bin/python core/test_text.py "brief me on my day"
"""
from __future__ import annotations
import asyncio
import sys

from dotenv import load_dotenv
load_dotenv(override=True)

from google_client import load_config
from brain import Brain
from tts import TTS
from tools import DISPATCH


async def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Brief me on my day."
    cfg = load_config()
    tts = TTS(cfg)
    brain = Brain(cfg, DISPATCH)

    async def on_sentence(s: str) -> None:
        print(f"🗣  {s}")
        await tts.speak(s)

    async def on_tool(name: str) -> None:
        print(f"🔧 {name}")

    print(f"👤 {prompt}\n")
    await brain.respond(prompt, on_sentence, on_tool)
    print("\n✅ done")


if __name__ == "__main__":
    asyncio.run(main())
