"""Assemble the exact tool set the production Muslim agent uses, by querying
every connected MCP server directly (not hardcoded) plus the two local
function_tools agent.py defines itself (play_ayah/play_surah)."""
from __future__ import annotations

import os

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

_ENV_LOCAL = os.path.join(
    os.path.dirname(__file__), "..", "..", "Muslim", "agent", ".env.local"
)


def _read_exa_api_key() -> str:
    if not os.path.exists(_ENV_LOCAL):
        return ""
    with open(_ENV_LOCAL, encoding="utf-8") as f:
        for line in f:
            if line.startswith("EXA_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


EXA_API_KEY = _read_exa_api_key()

# (label, url, transport, headers) -- mirrors Muslim/scripts/inspect_mcp.py and
# the servers wired into Muslim/agent/src/agent.py's mcp_servers=[...] list.
SERVERS = [
    ("validator", os.getenv("VALIDATOR_MCP_URL", "http://localhost:3001/sse"), "sse", None),
    ("islamic", os.getenv("ISLAMIC_MCP_URL", "http://localhost:3007/sse"), "sse", None),
    ("hadith", os.getenv("HADITH_MCP_URL", "http://localhost:3008/mcp"), "http", None),
    ("tafsir", "https://mcp.tafsir.net/mcp", "http", None),
    ("islamqa", "https://islamqa-mcp.org", "http", None),
    (
        "exa",
        "https://mcp.exa.ai/mcp",
        "http",
        {"Authorization": f"Bearer {EXA_API_KEY}"} if EXA_API_KEY else None,
    ),
]

# agent.py's own local function_tools -- not served by any MCP server.
LOCAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "play_ayah",
            "description": "تشغيل صوت آية محددة بصوت قارئ مختار.",
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer"},
                    "ayah": {"type": "integer"},
                    "reciter": {"type": "string"},
                },
                "required": ["surah", "ayah"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_surah",
            "description": "تشغيل تلاوة سورة كاملة بصوت قارئ مختار.",
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer"},
                    "reciter": {"type": "string"},
                },
                "required": ["surah"],
            },
        },
    },
]


async def _list_server_tools(url: str, transport: str, headers: dict | None):
    ctx = (
        sse_client(url, headers=headers)
        if transport == "sse"
        else streamablehttp_client(url, headers=headers)
    )
    async with ctx as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            return (await session.list_tools()).tools


async def fetch_all_tools() -> tuple[list[dict], dict[str, tuple[str, str, dict | None]]]:
    """Returns (openai_format_tools, tool_name -> (label, url, transport, headers))."""
    openai_tools = list(LOCAL_TOOLS)
    tool_to_server: dict[str, tuple[str, str, str, dict | None]] = {}

    for label, url, transport, headers in SERVERS:
        try:
            tools = await _list_server_tools(url, transport, headers)
        except Exception as e:
            print(f"WARNING: could not reach server '{label}' ({url}): {e}")
            continue
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            })
            tool_to_server[t.name] = (label, url, transport, headers)

    return openai_tools, tool_to_server
