import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def run(url, calls):
    out = []
    async with streamablehttp_client(url) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args in calls:
                try:
                    res = await session.call_tool(name, args)
                    content = "".join(c.text for c in res.content if hasattr(c, "text"))
                    out.append({"name": name, "args": args, "result": content[:1500]})
                except Exception as e:
                    out.append({"name": name, "args": args, "error": str(e)})
    return out

async def main():
    calls = [
        ("analyze_word", {"surah": 112, "ayah": 2, "word_no": 2}),  # الصمد
        ("analyze_word", {"surah": 108, "ayah": 1, "word_no": 3}),  # الكوثر
        ("analyze_word", {"surah": 113, "ayah": 1, "word_no": 4}),  # الفلق
        ("fetch_ayah", {"surah": 12, "ayah": 4}),
    ]
    res = await run("https://mcp.tafsir.net/mcp", calls)
    print(json.dumps(res, ensure_ascii=False, indent=2))

asyncio.run(main())
