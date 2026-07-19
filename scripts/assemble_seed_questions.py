"""Combine the four per-source seed files in data/sources/ into the final
data/seed_questions.jsonl used by later pipeline phases.

Run from the repo root: `python scripts/assemble_seed_questions.py`.
"""
import json

SOURCE_FILES = [
    "data/sources/seed_mode_finetuning.jsonl",
    "data/sources/seed_probes.jsonl",
    "data/sources/seed_voice_sessions.jsonl",
    "data/sources/seed_generated.jsonl",
]


def main():
    all_rows = []
    for fname in SOURCE_FILES:
        with open(fname, encoding="utf-8") as f:
            for line in f:
                all_rows.append(json.loads(line))

    with open("data/seed_questions.jsonl", "w", encoding="utf-8") as out:
        for i, row in enumerate(all_rows, start=1):
            row["id"] = f"q_{i:05d}"
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("total:", len(all_rows))
    from collections import Counter
    for source, count in Counter(r["source"] for r in all_rows).items():
        print(f"  {source}: {count}")


if __name__ == "__main__":
    main()
