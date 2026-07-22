"""One-off probe: list tools + call a handful of them on the two remote MCP
servers (mcp.tafsir.net, islamqa-mcp.org) to gather REAL ground-truth text for
authoring Muslim-v4 new-tool-coverage training examples. Prints JSON to stdout.
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def list_and_call(label, url, calls):
    out = {"label": label, "url": url, "tools": [], "calls": []}
    try:
        async with streamablehttp_client(url) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                for t in tools:
                    out["tools"].append({
                        "name": t.name,
                        "description": t.description or "",
                        "schema": t.inputSchema,
                    })
                for name, args in calls:
                    try:
                        res = await session.call_tool(name, args)
                        content = "".join(
                            c.text for c in res.content if hasattr(c, "text")
                        )
                        out["calls"].append({"name": name, "args": args, "result": content[:4000]})
                    except Exception as e:
                        out["calls"].append({"name": name, "args": args, "error": str(e)})
    except Exception as e:
        out["error"] = str(e)
    return out


async def main():
    tafsir_calls = [
        ("fetch_ayah", {"surah": 12, "ayah": 4}),
        ("fetch_tafsir", {"surah": 12, "ayah": 4}),
        ("list_tafsir_sources", {}),
        ("list_science_sources", {}),
        ("list_all_sources", {}),
        ("list_sources_for_ayah", {"surah": 2, "ayah": 255}),
        ("find_root_occurrences", {"root": "صبر"}),
        ("get_root_stats", {"root": "صبر"}),
        ("get_quran_overview", {}),
        ("get_page_fawaed", {"page": 1}),
        ("get_surah_statistics", {"surah": 12}),
    ]
    islamqa_calls = [
        ("search_answers", {"query": "حكم الزكاة على الذهب", "limit": 3}),
        ("search_answers", {"query": "أحكام صيام المسافر", "limit": 3}),
    ]

    tafsir_res, islamqa_res = await asyncio.gather(
        list_and_call("tafsir", "https://mcp.tafsir.net/mcp", tafsir_calls),
        list_and_call("islamqa", "https://islamqa-mcp.org", islamqa_calls),
    )
    print(json.dumps({"tafsir": tafsir_res, "islamqa": islamqa_res}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
