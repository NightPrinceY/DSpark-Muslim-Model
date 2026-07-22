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
                    out.append({"name": name, "args": args, "result": content[:3000]})
                except Exception as e:
                    out.append({"name": name, "args": args, "error": str(e)})
    return out

async def main():
    islamqa_calls = [
        ("list_categories", {}),
        ("fetch_answer", {"answer_id": 585436}),
        ("fetch_answer", {"answer_id": 50758}),
        ("fetch_grounding_rules", {}),
    ]
    res = await run("https://islamqa-mcp.org", islamqa_calls)
    print(json.dumps(res, ensure_ascii=False, indent=2))

asyncio.run(main())
