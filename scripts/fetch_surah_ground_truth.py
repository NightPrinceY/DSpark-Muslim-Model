"""Pull REAL, sourced ground truth for all 114 surahs from the live mcp.tafsir.net
server: fetch_surah_info (names/virtues/intro, incl. alternate-name scholarship)
and get_surah_statistics (ayah counts, revelation type, etc.).

This becomes the authoritative local cache for:
  1. Muslim-v4's systematic 114-surah coverage training examples.
  2. Cross-validating quran.json's SURA_NAME / SURA_COUNT against a second,
     independently-sourced authority before anything goes into training data.

Resumable: writes one line per surah to the output JSONL as it goes, skips
surahs already present on re-run.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "tafsir_net_surah_ground_truth.jsonl")
OUT = os.path.abspath(OUT)


def load_done():
    done = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                done[d["surah"]] = d
    return done


async def fetch_one(session, s):
    info = await session.call_tool("fetch_surah_info", {"surah": s, "include_en_intro": False})
    stats = await session.call_tool("get_surah_statistics", {"surah": s})
    info_text = "".join(c.text for c in info.content if hasattr(c, "text"))
    stats_text = "".join(c.text for c in stats.content if hasattr(c, "text"))
    return {
        "surah": s,
        "info": json.loads(info_text),
        "stats": json.loads(stats_text),
    }


async def main():
    done = load_done()
    print(f"already have {len(done)}/114", file=sys.stderr)
    async with streamablehttp_client("https://mcp.tafsir.net/mcp") as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            with open(OUT, "a", encoding="utf-8") as f:
                for s in range(1, 115):
                    if s in done:
                        continue
                    try:
                        row = await fetch_one(session, s)
                    except Exception as e:
                        print(f"surah {s} FAILED: {e}", file=sys.stderr)
                        await asyncio.sleep(2)
                        continue
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"surah {s} done", file=sys.stderr)
                    await asyncio.sleep(0.3)
    print("ALL DONE", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
