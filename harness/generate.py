"""Agentic generation harness: drives Muslim-6B-v3 (served via vLLM with
tool-calling) through the seed question bank, executing real tool calls
against the real MCP servers, and writes the resulting conversations in
DeepSpec's expected {"conversations": [...]} JSONL schema.

Run from the repo root: `python harness/generate.py`.
Resumable: rerunning skips ids already present in the output file.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys

from openai import AsyncOpenAI

sys.path.insert(0, os.path.dirname(__file__))
from dispatch import MCPDispatcher, parse_tool_arguments  # noqa: E402
from tools import fetch_all_tools  # noqa: E402

MODEL = "NightPrince/Muslim-6B-v3"
BASE_URL = "http://localhost:8000/v1"
SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed_questions.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.jsonl")
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.txt")

MAX_ROUNDS = 4
CONCURRENCY = 8
TEMPERATURE = 0.7
MAX_TOKENS = 400

MARKDOWN_RE = re.compile(r"[*#`_]{1,}|\[.*?\]\(.*?\)")
DIGIT_RE = re.compile(r"[0-9٠-٩]")  # ASCII + Eastern Arabic-Indic digits


def load_seed_questions() -> list[dict]:
    with open(SEED_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_done_ids() -> set[str]:
    if not os.path.exists(OUT_PATH):
        return set()
    done = set()
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def validate_conversation(conversations: list[dict]) -> str | None:
    """Returns an error string if invalid, else None."""
    if len(conversations) < 2:
        return "too short"
    if conversations[0]["role"] != "system" or conversations[1]["role"] != "user":
        return "bad role sequence start"
    if conversations[-1]["role"] != "assistant":
        return "does not end on assistant turn"
    for i in range(1, len(conversations)):
        role = conversations[i]["role"]
        prev = conversations[i - 1]["role"]
        if role == "tool" and prev not in ("assistant", "tool"):
            return f"tool turn at {i} not preceded by assistant/tool"
    final_text = conversations[-1].get("content") or ""
    if MARKDOWN_RE.search(final_text):
        return "final answer contains markdown"
    if DIGIT_RE.search(final_text):
        return "final answer contains raw digits (not TTS-clean)"
    return None


async def generate_one(
    client: AsyncOpenAI,
    dispatcher: MCPDispatcher,
    openai_tools: list[dict],
    system_prompt: str,
    question: dict,
    out_file,
    write_lock: asyncio.Lock,
) -> None:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question["text"]},
    ]

    for _ in range(MAX_ROUNDS):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
        except Exception as e:
            print(f"[{question['id']}] request failed: {e}")
            return

        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                try:
                    args = parse_tool_arguments(tc.function.arguments)
                except Exception:
                    args = {}
                result = await dispatcher.dispatch(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })
        else:
            messages.append({"role": "assistant", "content": msg.content or ""})
            break
    else:
        # hit MAX_ROUNDS without a final answer -- discard, don't force a bad record
        print(f"[{question['id']}] hit max rounds without final answer, skipping")
        return

    error = validate_conversation(messages)
    if error:
        print(f"[{question['id']}] rejected: {error}")
        return

    record = {
        "id": question["id"],
        "source": question.get("source"),
        "intent": question.get("intent"),
        "conversations": messages,
    }
    async with write_lock:
        out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_file.flush()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="process at most N questions (for testing)")
    args = parser.parse_args()

    questions = load_seed_questions()
    done_ids = load_done_ids()
    todo = [q for q in questions if q["id"] not in done_ids]
    if args.limit:
        todo = todo[: args.limit]
    print(f"total questions: {len(questions)}, already done: {len(done_ids)}, remaining: {len(todo)}")
    if not todo:
        return

    with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
        system_prompt = f.read()

    print("fetching tool schemas from all MCP servers...")
    openai_tools, tool_to_server = await fetch_all_tools()
    print(f"assembled {len(openai_tools)} tools from {len(set(v[0] for v in tool_to_server.values()))} servers")

    client = AsyncOpenAI(base_url=BASE_URL, api_key="not-needed")
    write_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def bounded(q):
        async with semaphore:
            await generate_one(client, dispatcher, openai_tools, system_prompt, q, out_file, write_lock)

    async with MCPDispatcher(tool_to_server) as dispatcher:
        with open(OUT_PATH, "a", encoding="utf-8") as out_file:
            tasks = [asyncio.create_task(bounded(q)) for q in todo]
            completed = 0
            for coro in asyncio.as_completed(tasks):
                await coro
                completed += 1
                if completed % 25 == 0:
                    print(f"progress: {completed}/{len(todo)}")

    print("done.")


if __name__ == "__main__":
    asyncio.run(main())
