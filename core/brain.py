"""J.A.R.V.I.S. brain — Claude (AsyncAnthropic) with tool use, prompt caching,
and streaming responses chunked into sentences for low-latency TTS."""
from __future__ import annotations
import re
from typing import Awaitable, Callable

import anthropic

from prompts import system_prompt, context_message, TOOLS

# Emit a sentence to TTS as soon as a boundary is seen, so speech starts early.
_SENTENCE_END = re.compile(r"(.+?[.!?…])(\s+|$)", re.DOTALL)

OnSentence = Callable[[str], Awaitable[None]]   # speak this sentence
OnTool = Callable[[str], Awaitable[None]]        # tool name about to run (HUD chip)


class Brain:
    def __init__(self, cfg: dict, tool_dispatch: dict[str, Callable[..., Awaitable[str]]]):
        self.client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
        b = cfg["brain"]
        a = cfg["assistant"]
        self.model = b.get("model", "claude-opus-4-8")
        self.effort = b.get("effort", "low")
        self.max_tokens = int(b.get("max_tokens", 1024))
        self.tool_dispatch = tool_dispatch
        # System prompt as a cacheable block (tools render before it, so this caches both).
        self._system = [{
            "type": "text",
            "text": system_prompt(a.get("address", "Doctor"), a.get("language", "English")),
            "cache_control": {"type": "ephemeral"},
        }]
        self.history: list[dict] = []

    async def respond(self, user_text: str, on_sentence: OnSentence, on_tool: OnTool) -> str:
        """Run the agentic loop for one user turn. Streams sentences to `on_sentence`.
        Returns the full spoken text."""
        # Volatile context (time) goes in the user turn, never the cached system prefix.
        self.history.append({
            "role": "user",
            "content": f"{context_message()}\n\n{user_text}",
        })

        spoken_parts: list[str] = []
        while True:
            buf = ""
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system,
                tools=TOOLS,
                output_config={"effort": self.effort},
                thinking={"type": "disabled"},
                messages=self.history,
            ) as stream:
                async for text in stream.text_stream:
                    buf += text
                    buf = await self._flush_sentences(buf, on_sentence, spoken_parts)
                final = await stream.get_final_message()

            # Flush any trailing text that didn't end on a sentence boundary.
            tail = buf.strip()
            if tail:
                spoken_parts.append(tail)
                await on_sentence(tail)

            self.history.append({"role": "assistant", "content": final.content})

            if final.stop_reason != "tool_use":
                break

            # Execute every requested tool, return all results in one user turn.
            tool_results = []
            for block in final.content:
                if block.type != "tool_use":
                    continue
                await on_tool(block.name)
                try:
                    fn = self.tool_dispatch[block.name]
                    result = await fn(**(block.input or {}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                except Exception as e:  # surface errors to Claude so it can adapt
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })
            self.history.append({"role": "user", "content": tool_results})

        return " ".join(spoken_parts).strip()

    @staticmethod
    async def _flush_sentences(buf: str, on_sentence: OnSentence, parts: list[str]) -> str:
        """Emit each complete sentence in `buf`; return the unflushed remainder."""
        while True:
            m = _SENTENCE_END.match(buf)
            if not m:
                return buf
            sentence = m.group(1).strip()
            if sentence:
                parts.append(sentence)
                await on_sentence(sentence)
            buf = buf[m.end():]
