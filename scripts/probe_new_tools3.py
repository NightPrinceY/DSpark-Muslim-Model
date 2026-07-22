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
                    out.append({"name": name, "args": args, "result": content[:2500]})
                except Exception as e:
                    out.append({"name": name, "args": args, "error": str(e)})
    return out

async def main():
    tafsir_calls = [
        ("analyze_word", {"surah": 2, "ayah": 45, "word_no": 2}),
        ("analyze_word", {"surah": 1, "ayah": 1, "word_no": 2}),
        ("fetch_ayah", {"surah": 55, "ayah": 13}),
        ("fetch_tafsir", {"surah": 24, "ayah": 35, "sources": ["saadi"]}),
        ("fetch_nuzool_reason", {"surah": 111, "ayah": 1}),
        ("fetch_nuzool_reason", {"surah": 93, "ayah": 1}),
        ("fetch_surah_info", {"surah": 18}),
        ("get_surah_statistics", {"surah": 67}),
        ("get_page_fawaed", {"page": 30}),
        ("find_root_occurrences", {"root": "علم", "limit": 5}),
        ("get_root_stats", {"root": "رحم"}),
        ("list_sources_for_ayah", {"surah": 112, "ayah": 1}),
        ("search_in_tafsir", {"query": "الصبر", "source": "saadi", "limit": 3}),
        ("get_qeraat_variants", {"surah": 1, "ayah": 4}),
    ]
    islamqa_calls = [
        ("search_answers", {"query": "أحكام الحج للمرأة", "limit": 2}),
        ("search_answers", {"query": "حكم الربا في المعاملات البنكية", "limit": 2}),
        ("search_answers", {"query": "حقوق الزوجة في الإسلام", "limit": 2}),
    ]
    tafsir_res = await run("https://mcp.tafsir.net/mcp", tafsir_calls)
    islamqa_res = await run("https://islamqa-mcp.org", islamqa_calls)
    print(json.dumps({"tafsir": tafsir_res, "islamqa": islamqa_res}, ensure_ascii=False, indent=2))

asyncio.run(main())
