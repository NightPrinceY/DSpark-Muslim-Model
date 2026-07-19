"""Extract user turns from Muslim-mode-finetuning's hand-curated LoRA dataset.

We only take the user question + its behavior/intent tags -- the old assistant
answers are discarded, since Phase 2+ regenerates fresh answers by actually
running each question through Muslim-6B-v3 + live MCP tools.

Requires a local clone of github.com/NightPrinceY/Muslim-mode-finetuning
(`gh repo clone NightPrinceY/Muslim-mode-finetuning`). Point --repo-dir at it.

Run from the repo root: `python scripts/extract_mode_finetuning.py --repo-dir <path>`.
"""
import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True, help="Path to cloned Muslim-mode-finetuning repo")
    parser.add_argument("--out", default="data/sources/seed_mode_finetuning.jsonl")
    args = parser.parse_args()

    dataset_dir = os.path.join(args.repo_dir, "dataset")
    out_rows = []
    idx = 1
    for fname in ["muslim_lora_train_v2.jsonl", "muslim_lora_val_v2.jsonl"]:
        with open(os.path.join(dataset_dir, fname), encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                user_text = next(m["content"] for m in rec["messages"] if m["role"] == "user")
                out_rows.append({
                    "id": f"mft_{idx:04d}",
                    "text": user_text,
                    "behavior": rec["behavior"],
                    "intent": rec["intent"],
                    "source": "mode_finetuning",
                })
                idx += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as out_f:
        for row in out_rows:
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
