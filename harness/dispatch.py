"""Persistent MCP connections + tool-call dispatch for the generation harness."""
from __future__ import annotations

import json
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

RECITERS_AUDIO = [
    "Minshawy_Murattal_128kbps", "Minshawy_Mujawwad_64kbps", "Alafasy_128kbps",
    "Husary_128kbps", "Abdurrahmaan_As-Sudais_192kbps", "Maher_AlMuaiqly_64kbps",
]

MAX_TOOL_RESULT_CHARS = 3000  # some tools (e.g. get_tafsir_surah on long surahs) can
                              # return many thousands of characters -- the 37-tool
                              # schema (~8.7K tokens) gets resent every round, so
                              # unbounded tool results blow the context budget fast.


class MCPDispatcher:
    """Opens one persistent session per MCP server and routes tool calls to it.

    play_ayah/play_surah aren't MCP tools (they're agent.py's own local
    function_tools that stream real audio over LiveKit) -- here we validate
    the request against IslamicMCPServer's get_ayah_audio/get_surah_audio
    (same underlying data) and return the same style of confirmation/error
    text production actually returns, without needing a real audio session.
    """

    def __init__(self, tool_to_server: dict[str, tuple[str, str, str, dict | None]]):
        self.tool_to_server = tool_to_server
        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}  # label -> session

    async def __aenter__(self):
        await self._stack.__aenter__()
        seen_labels = set()
        for name, (label, url, transport, headers) in self.tool_to_server.items():
            if label in seen_labels:
                continue
            seen_labels.add(label)
            ctx = (
                sse_client(url, headers=headers)
                if transport == "sse"
                else streamablehttp_client(url, headers=headers)
            )
            streams = await self._stack.enter_async_context(ctx)
            session = await self._stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
            self._sessions[label] = session
        return self

    async def __aexit__(self, *exc):
        await self._stack.__aexit__(*exc)

    async def _call_mcp_tool(self, name: str, arguments: dict) -> str:
        label, *_ = self.tool_to_server[name]
        session = self._sessions[label]
        result = await session.call_tool(name, arguments)
        parts = []
        for block in result.content:
            parts.append(getattr(block, "text", str(block)))
        text = "\n".join(parts)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + " …[تم اختصار النتيجة]"
        return text

    async def dispatch(self, name: str, arguments: dict) -> str:
        try:
            if name == "play_ayah":
                return await self._mock_play_ayah(arguments)
            if name == "play_surah":
                return await self._mock_play_surah(arguments)
            if name not in self.tool_to_server:
                return f"خطأ: الأداة {name} غير متوفرة."
            return await self._call_mcp_tool(name, arguments)
        except Exception as e:
            return f"عذرًا، حدث خطأ أثناء تنفيذ الطلب: {e}"

    async def _mock_play_ayah(self, arguments: dict) -> str:
        surah = arguments.get("surah")
        ayah = arguments.get("ayah")
        reciter = arguments.get("reciter") or "Minshawy_Murattal_128kbps"
        if "islamic" not in self._sessions:
            return "Audio playback finished."
        result = await self._call_mcp_tool(
            "get_ayah_audio", {"surah": surah, "ayah": ayah, "reciter": reciter}
        )
        if result.startswith("http"):
            return "Audio playback finished."
        return result  # error text from the tool (invalid reciter/verse etc.)

    async def _mock_play_surah(self, arguments: dict) -> str:
        surah = arguments.get("surah")
        reciter = arguments.get("reciter") or "muhammad_siddeeq_al-minshaawee"
        if "islamic" not in self._sessions:
            return "تم تشغيل السورة كاملة."
        result = await self._call_mcp_tool(
            "get_surah_audio", {"surah": surah, "reciter": reciter}
        )
        if result.startswith("http"):
            return "تم تشغيل السورة كاملة."
        return result


def parse_tool_arguments(raw: str) -> dict:
    """Muslim-6B-v3 consistently double-JSON-encodes tool call arguments
    (traced to a chat-template `| tojson` bug in its own training data --
    verified this session). Keep decoding while the result is still a string."""
    value = raw
    for _ in range(3):
        if not isinstance(value, str):
            break
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError(f"Could not parse tool arguments into a dict: {raw!r}")
    return value
